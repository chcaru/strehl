# M58 — audit of the SYNTHESIS fold itself (commits `d7eedfa`..`9715bad`)

**Milestone M58 (fold-fidelity audit).** Read-only with respect to `crates/**`,
`SYNTHESIS.md`, `AGENTS.md` and `OWNER-QUESTIONS.md`. This file is the only thing
this milestone writes.

**Question under audit:** not "was M48b/M54/M55/M56 right", but "does SYNTHESIS say
what those reports say". Nine commits, facts 663-725, disciplines 329-347, questions
155-171, twenty-four amended pre-existing fact rows, six reopened/withdrawn questions,
and OWNER-QUESTIONS items 32-38.

Labels per rule 8. **MEASURED** = I ran a command and read the output. **DERIVED** =
exact arithmetic on measured or published quantities. **ARGUED** = reasoning from
structure, no new number.

## 0. Verdict

**The fold is largely faithful and the structural machinery is now clean, but the
folder's own self-audit row is false, and two rows that should have been amended were
not.** Three findings are HIGH. All four self-reported defect classes (facts 679, 693,
694, rule 37) are repaired and stay repaired: **MEASURED**, at `9aca35f`, 516 fact rows,
zero rows with the wrong unescaped-pipe count, zero duplicate numbers, zero missing
numbers in 663-725 / 329-347 / 155-171, zero numbered items in the wrong section, and
the file ends in exactly one newline.

Every finding below is stated with the SYNTHESIS text, the source text, and a
reproduction command.

---

## 1. HIGH

### H1 — Fact 725 is false on its own enumeration, and fact 613 was left internally false

*Classification: structural defect + omitted amendment. Commit `9aca35f`.*

**SYNTHESIS 725** (L1286): "Refuting the corpus's most-cited recent result touched only
**7 of 515 fact rows**, and **exactly ONE of them became internally false** as a result.
A sweep for rows depending on facts 610, 619, 620 and 640 found **613, 618, 622, 623,
639, 645, 650 and 652**."

**MEASURED.** That list has **eight** members, not seven.

**MEASURED.** `git --no-pager show 9aca35f -- docs/research/SYNTHESIS.md` modifies exactly
seven fact rows — 618, 622, 623, 639, 645, 650, 652 — plus the new row 725. **Fact 613 is
named in the sweep and was never touched.**

**MEASURED.** Fact 613's Consequence at HEAD still reads: "the **FRC value at `f_sig`
survives** and is a load-bearing ingredient of **fact 619's admissible metric**." Fact 619
now reads "(**REFUTED by facts 695, 703-706 … NOT ADMISSIBLE.**)".

**DERIVED.** Fact 613 therefore asserts the existence of an admissible metric that the
same session withdrew — the identical failure shape 725 says occurred exactly once. Both
of 725's headline claims are wrong: the count (7 vs 8) and the central finding (one row
became internally false vs at least two).

**Why it matters (ARGUED):** 725 is the row a future reader will cite for "the fact table
is loosely coupled, and that is a design property worth knowing". It is the folder's own
measurement of the blast radius of a refutation, and it under-reports that radius.

### H2 — Fact 610 was never amended, and still advertises a confirmation the same session measured as powerless

*Classification: omitted amendment. Commits `57632ff`, `9aca35f`.*

**SYNTHESIS 610** (L1171), Consequence, unchanged: "one of the few genuinely
**out-of-sample confirmations** in this corpus. Most agreement here has been in-sample;
this one predicted a number on a source the parameter was not fitted to and **hit it to
0.4%**." Source column: `M46 (MEASURED) DERIVED, confirmed MEASURED`.

**SYNTHESIS 697** (L1258), folded in the same session: "**Fact 610 is refuted out of
sample, and its confirmation had no power.** … the measured dark FPN on the ISO-500 quad
plane is 0.2888 DN (variance 0.08341) — a **231x shortfall in variance**. And planting
`rho` anywhere from **0.02 to 3.0** passes the same check at 0.966-1.000."

**MEASURED.** Fact 610 carries only the M48b marker "SCOPED by facts 670-672". It contains
**no reference to fact 697 and no refutation marker of any kind.**
`git --no-pager show 57632ff -- docs/research/SYNTHESIS.md` amends 617, 619, 620, 640,
641, 644, 649 — not 610. `9aca35f` amends 618, 622, 623, 639, 645, 650, 652 — not 610.

**ARGUED.** A reader of §4 alone reads 610 as live, confirmed, and one of the corpus's
best results. AGENTS rule 39 and OWNER-QUESTIONS items 33/37 record the refutation; the
durable record does not. The `9aca35f` sweep was scoped to rows *depending on* the
refuted facts and never revisited the refuted facts themselves — which is why 610 and
619/620/640 diverge in treatment (619, 620 and 640 all carry inline REFUTED markers).

### H3 — Fact 202's headline is now false, and fact 680 says so in the same file

*Classification: unsupported amendment / internal inconsistency. Commit `7ebfdfa`.*

**SYNTHESIS 202** (L890) headline, unchanged: "**Saturation is real, per-stack, and absent
from four of six stacks.**" Amendment added by the M54 fold: "(**PARTLY REFUTED by fact
680: `113MSDCF` is NOT clipping-free — 58 green samples sit at the 16383 container max, a
real specular highlight. `109`, `112` and `119MSDCF` remain exactly zero.**)"

**SYNTHESIS 680** (L1241): "`113MSDCF` **must be struck from every list of clipping-free
stacks**."

**DERIVED.** With 113 struck, saturation is absent from **three** of six stacks, not four.
The bolded count at the head of the row was not updated, so the row's own amendment
contradicts its own headline — and the instruction fact 680 issues is disobeyed inside the
very row it was folded to amend.

**ARGUED.** This is the same shape as fact 622, which `9aca35f` found by hand and which
fact 725 claims was unique. It is a second instance, in a different fold, and it is a
bolded number in the first sentence of a row.

---

## 2. MODERATE

### M1 — "Four of the six failing cells are flat" is not in the source and is false on the source's own table

*Classification: transcription error (orchestrator-invented). Commit `57632ff`.*

**SYNTHESIS 707** (L1268): "The explanation fact 641 gives is right for detail and does not
cover the flat case, **which is where four of the six failing cells sit**."
**SYNTHESIS question 165** (L3306) repeats it: "An unidentified mechanism operates on flat
regions, and **four of the six failing cells are flat**."

**MEASURED.** `M55-sigpow-verification.md` §5.4's table has six rows; the ROI column reads
detail, flat, centre, flat, centre, flat — **three flat of six**. All six fail (none
reaches 0.90). §6.2 (L512) says "**flat ROIs** (113 flat is `K`-independent at
0.350/0.353/0.357; 112 and foam go more negative)" — three again. §6.3 lists 7 of 36
negative cells, six of those flat — a different denominator.

**ARGUED.** No reading of the source makes "four of the six failing cells are flat" true.
The likely origin is M55's own (also wrong) "four of six are below 0.5" at L271/L517,
conflated with the flat-ROI discussion.

### M2 — Fact 696 transcribes an arithmetic error visible in its own sentence

*Classification: transcription of a false source claim. Commit `57632ff`.*

**SYNTHESIS 696** (L1257): "**0.368, 0.635, 0.366, 0.037, 0.739, 0.549** — none reaching
0.90, **four of six below 0.5**."

**DERIVED.** Three of those six are below 0.5 (0.368, 0.366, 0.037).

**MEASURED.** The source says the same thing twice (M55 L271, L517), so the fold is
transcription-faithful. But rule 28 asks the folder to check by content, and the six
numbers sit in the same sentence as the count. The durable record now carries a false
count with no marker.

### M3 — Fact 627's new amendment cites fact 723 for a claim fact 723 does not contain

*Classification: citation defect. Commit `0b0604e` — the same commit that establishes
"resolving is not supporting".*

**MEASURED.** `git --no-pager show 0b0604e -- docs/research/SYNTHESIS.md` adds to fact 627:
"(**Its ISO attribution is WRONG: fact 723's audit finds `113MSDCF` and `112MSDCF` are ISO
500, not ISO 160.**)"

**MEASURED.** SYNTHESIS fact 723 (L1284) is entirely about `strehl-plugin` citing facts
436/439/509 without their later scopings. It contains no ISO claim and does not name
`113MSDCF` or `112MSDCF`.

**MEASURED.** The underlying claim is true and is supported — by **fact 656** (L1217):
"`112MSDCF`/`113MSDCF` ISO 500, `coffee-bubbles`/`foam` ISO 1000".

**ARGUED.** This is fact 713's own defect class (a number resolving to a real row that does
not support the sentence), committed in the fold that introduced fact 713, discipline 343
and AGENTS rule 38. If "723" is instead an M56 report-local number, it is fact 717's defect
class instead.

### M4 — Facts 717 and 719 contradict each other about `profile.rs:92`, and 719's "all cite fact 200" is false

*Classification: transcription error / unsupported fold claim. Commit `0b0604e`.*

**SYNTHESIS 719** (L1280): "`profile.rs` has **FOUR** mis-cited sites, not three … At
`d7eedfa` they are `:72, :87, :92, :112`, not `:25, :40, :45`. **All cite "M25 fact 200"**".
**SYNTHESIS 717** (L1278): "Same defect at `stack.rs:358` and **`profile.rs:92`**" — i.e.
`:92` is a *`200a`* site.

**MEASURED.** `git --no-pager show d7eedfa:crates/strehl-core/src/profile.rs`:

```
 :72   /// **MEASURED at ISO 160, by photon transfer on signal** (M25 fact 200):
 :87   /// 1.0021 where a genuine gain step demands 0.5. M25 fact 200 from signal,
 :92   /// **The boundary itself is not measured** (M25 fact 200a): the corpus holds
:112   /// corpus's real stacks are ISO 50 and ISO 160 (M25 fact 200's table).
```

**DERIVED.** `:92` cites `200a`, not `200`. So 719's "All cite 'M25 fact 200'" is false, and
the count "FOUR … not three" appears to come from a substring match on `fact 200` that
swallowed `fact 200a`. Fact 581's original count of three was right; only its line numbers
had rotted. Two rows in the same fold classify the same line differently.

*(Corroborating, out of scope: the later commit `cc2af9f` / fact 726 records M48
independently re-verifying all four sites and disagreeing with 719's characterisation.)*

### M5 — Fact 622's repair is half done: the Consequence column still asserts what the headline was repaired to withdraw

*Classification: structural defect. Commit `9aca35f`.*

**SYNTHESIS 622** (L1183) headline after repair: "(closes question 119 — **question 119 is
REOPENED by facts 695-706; this row no longer closes it**)". Consequence column, unchanged:
"**Question 119 is answered negatively** and the general rule is worth more than the
answer…". Question 119 at HEAD: "**REOPENED, and it is now the project's largest blocker
again.**"

**ARGUED.** A charitable reading survives — 622 answers 119's *paired-statistic*
sub-question negatively, and that half explicitly stands. But as written, the two cells of
one row contradict each other on the same question number, and this is the exhibit row for
fact 725's "an amendment does not propagate to what cites it". The repair fixed the first
cell and not the second.

### M6 — Fact 694 misstates its own repair, and a provenance edit rode in under a pipe-escaping commit

*Classification: transcription error + undisclosed edit. Commits `606c8f7`, `7ebfdfa`.*

**SYNTHESIS 694**: rows 617/621/624 carried unescaped bars; "**Two of them** additionally
carried a malformed provenance cell (`M46 (MEASURED) DERIVED + MEASURED`)."

**MEASURED** at `606c8f7`, counting `|` after stripping `\|`: rows with 7 unescaped pipes =
{617, 621, 624}. Rows carrying `M46 (MEASURED) DERIVED + MEASURED` = {617, **620**}.
Intersection = {617} — **one** of them, not two. Row 620 had exactly 5 unescaped pipes and
rendered correctly; it is an unrelated fourth row.

**MEASURED.** `7ebfdfa` rewrote the provenance of **617 and 620** to `M46 (DERIVED +
MEASURED)`. 620's rewrite is a semantic provenance change unconnected to the pipe defect,
made inside a commit whose stated subject was escaping and folding, and mis-recorded in the
row that documents it.

### M7 — Fact 688 and discipline 333 drop the stack scope, making a false general claim

*Classification: transcription error (dropped qualifier). Commit `7ebfdfa`.*

**SYNTHESIS 688**: "mean `n_eff` on the winner-clipped population is **1.023**, so at least
**97.7%** of it sits where the statistic could not move."
**Discipline 333**: "which was **97.7% of the population** it was chosen to decide."

**MEASURED.** `M54-clip-mask-measured.md` scopes 1.023 to **`coffee-bubbles`**;
`coffee-bean`'s WINCLIP mean `n_eff` is 1.881 at gate 0.5 and 28.784 at gate 4.0, where
the deficit statistic is *not* structurally zero for most of the population.

**ARGUED.** Both rows state as a property of the statistic what the source states as a
property of one stack.

### M8 — Fact 709 undercounts the verifier's self-refutations

*Classification: transcription error. Commit `57632ff`.*

**SYNTHESIS 709**: "The verifier refuted **two** of its own positions, **one of them**
pre-registered."
**Source, M55 §1**: "**Three** of the twenty-four refuted my own stated objection (PR7,
PR11, PR21)." Both instances the row goes on to cite (PR7, PR11) are themselves
pre-registered.

**ARGUED.** The error runs against the verifier's credit, in a row whose entire point is
that recording self-refutation is what makes the other findings credible.

---

## 3. LOW

### L1 — `S` range quoted as 0.770-0.976 where the source says 0.770-0.980, in four places

**MEASURED.** M55 states "0.770 to 0.980" three times (L3, L315, L489); the §5.6 table gives
REPS = 16 -> **0.980**, the maximum. SYNTHESIS quotes "0.770-0.976" in **fact 640's
amendment**, **discipline 338**, and **AGENTS rule 39**. Fact 695 itself is clean — it
quotes four exact rows (0.770 / 0.976 / 0.937 / 0.972 at 1 / 8 / 32 / 64) — but the subset
it chose omits the extremum, and the three range statements inherit that omission.
*Direction: understates the instability the finding exists to demonstrate.*

### L2 — Fact 708 pairs mismatched adversaries

**SYNTHESIS 708**: "FRC reads **+0.0001** against a linear post-filter and the oracle reads
**+0.00003**."
**MEASURED.** M55 §2.1 gives sigpow `+0.0001` vs a **linear post-filter** and `+0.00005` vs
a **contrast-restoring low-pass**. §7.1 gives the oracle's `+0.00003` **against the
contrast-restoring low-pass**, paired with sigpow's `+0.00005`. The row implies both figures
share one adversary; the source never makes that comparison.

### L3 — Fact 673 cites fact 655 for a figure fact 655 does not carry

**SYNTHESIS 673**: "**fact 655** measured the 0.1st-percentile pixel of a real high-ISO
stack at **132 DN**".
**MEASURED.** SYNTHESIS 655 (L1216) says only "the darkest 0.1% of the ISO-1000 stack sits
**27x above it**". `132 DN` appears in `M48-read-noise-measured.md` local fact 25 and in
SYNTHESIS **question 153** — not in 655. Resolving is not supporting.

### L4 — "on every run" is a scope overstatement in fact 717 and in OWNER-QUESTIONS item 36

**MEASURED**, `git --no-pager show 0b0604e:crates/strehl-cli/src/stack.rs`: `provenance_line`
at `:353` matches on `noise.provenance`. The `fact 200a` string lives only in the
`Provenance::Profile` arm (`:361`-`:390`). `Provenance::Measured` (`:391`) and
`Provenance::Fallback` (`:395`) do not contain it.
**SYNTHESIS 717**: "prints "fact 200a" **on every `stack` and `merge` run**".
**OWNER-QUESTIONS item 36**: "**Every single run** prints a citation to "fact 200a"".
*Mitigation: `Profile` is presumably the usual path for a profiled body. The claim is still
stated unconditionally where the code is conditional.*

### L5 — Fact 724 quotes the pre-registration with the violated clause removed

**MEASURED**, `git --no-pager show fe6893a`: the pre-registered condition in §8 ended
"— the corpus has now spent three milestones on that hunt and **a fourth is not obviously
repayable**." Fact 724's quotation stops at "…rather than to keep hunting for a metric."
— omitting exactly the clause the folder then overrides. §8 itself quotes it in full, and
724's Consequence does disclose "one bounded override".

**Note, and it runs the other way:** OWNER-QUESTIONS item 38 paraphrases the same clause as
a flat prohibition — "*and do not start a fourth hunt for a metric*" — which is **stronger
than the original**, and then discloses violating it. Two inaccurate renderings of one
pre-registration, in opposite directions; the owner-facing one is the self-incriminating one.

### L6 — Fact 689's "nearly three orders of magnitude" is unsupported and compares incommensurable denominators

**SYNTHESIS 689**: "An early harness called **35% of clipped pixels** diluted on that basis;
per-plane accounting gives **0.0004-0.0028% of samples**." Consequence: "**Nearly three
orders of magnitude**".
**MEASURED.** The source (`M54` §5 item 2) states no order-of-magnitude figure.
**DERIVED.** 35 / 0.0028 = 1.25e4 (4.1 orders); 35 / 0.0004 = 8.75e4 (4.9 orders). Neither
is "nearly three", and the two percentages have different denominators (clipped pixels vs
all samples), so the ratio is not well defined as stated.

### L7 — Fact 676 misattributes question 20's hypothesis and reopens a closed question

**SYNTHESIS 676**: "Bears directly on **question 20's** orientation anomaly, **which
hypothesised row/column FPN as the mechanism** … so the anomaly **needs another
explanation**."
**MEASURED.** Question 20 (L2810) hypothesises **texture anisotropy** or a `|d| <= 24`
**band-geometry defect**; row/column FPN was the *external review's* proposed fix, not the
question's hypothesis. Question 20 is **CLOSED by facts 90-92** with a measured mechanism
(texture anisotropy; 14-22x more vertical gradient energy), and **fact 93** already refuted
the row-FPN mechanism at all 11 ISOs.
**MEASURED.** `M48b-fpn-rho-measured.md` never mentions question 20. The link is
orchestrator-added, and it presents a closed question as needing another explanation.

### L8 — Fact 681 drops the source's scope

`M54-3` scopes the clip histogram to **`coffee-bean`**, 11 frames sampled every 10th.
SYNTHESIS 681 states the counts unscoped, as a property of "the data".

### L9 — Discipline 340's citation is self-referential

"(M55, facts 705 and **340's own mechanism**)" resolves to nothing. The content is supported
(M55 L428, L541, L598); only the citation is malformed.

### L10 — `d7eedfa` under-reports its own deletions

The commit message claims "two accounted-for deletions". **MEASURED**: the SYNTHESIS diff
has three — fact 610's old line, fact 612's old line, and the blank line before question
143. AGENTS rule 29's tell, at the commit that introduced the trailing-newline defect.

### L11 — Question 142's continuation is indented one space, not five

**MEASURED.** The ANSWERED continuation added to question 142 is indented 1 space, against
the file's five-space convention, and consumed the blank line separating items 142 and 143.
It renders acceptably as a lazy continuation, but rule 37's item-anchoring relies on that
convention holding.

### L12 — Fact 612's amplitude was not rescoped

**Source, M55 §2.4** (L63): "Fact 612's whiteness sub-claim survives; **its amplitude does
not**."
**MEASURED.** Fact 612 states "Adding FPN at `rho = 0.3094` pins the crossing at 0.4961
[CENSORED]" and carries only the M48b whiteness confirmation. It was amended by neither
the M55 fold nor the `9aca35f` sweep (which was scoped to rows depending on 610/619/620/640
and matched 612 on none of those numbers). The row still uses a refuted amplitude as the
injected FPN level with no marker.

---

## 4. Provenance: the M56 fold has no committed source

*Classification: process defect. Commit `0b0604e`. AGENTS rule 31.*

**MEASURED.** `git --no-pager log --all --name-only --pretty=format: | Select-String M56`
returns nothing. No `docs/research/M56*.md` exists in any commit or in the worktree.
`Get-ChildItem -Recurse -Force -Filter "*M56*"` finds only the **untracked**
`experiments/M56-citations/` directory and two build artefacts.

**MEASURED.** All eleven rows 713-723 cite `M56 (MEASURED)`; disciplines 343-347 and
questions 168-171 cite `(M56, fact NNN)`. No sha appears in any Source cell.

**AGENTS rule 31**: "**Fold from a committed revision, and record its sha in the source
column.** … A report cannot describe what a fold says; only the fold can."

**Consequence for this audit (ARGUED):** facts 713-723 are the one block in scope that
**cannot be audited for fidelity**, because there is no source text to compare against.
I verified them directly against `crates/` at `0b0604e` instead:

| row | independent check | result |
|---|---|---|
| 714 | `merge_cmd.rs:1284` prints "0.868% (Tenengrad, regularised)"; `strehl-core/src/stack.rs:176` duplicates it | **CONFIRMED** |
| 715 | five sites: `examples/f5-design-probes.rs:141`, `src/calibrate.rs:40`, `:100`, `src/lib.rs:58`, `src/measure.rs:83` | **CONFIRMED**, exact line numbers |
| 717 | `stack.rs` prints `fact 200a` | **CONFIRMED with narrower scope** — see L4; and contradicts 719, see M4 |
| 718 | 3516x2344 = 8,241,504 px; x60 B = 494.5 MB, x64 B = 527.5 MB, 64/60 = +6.67%; `main.rs:166` fixed in `e48d0f7` | **CONFIRMED (DERIVED)** |
| 719 | `profile.rs` `:72,:87,:92,:112` at `d7eedfa` | **PARTLY REFUTED** — see M4 |
| 720 | `the_solved_gate_spans_the_range_fact_324_claims` at `merge_cmd.rs:2001` | **CONFIRMED**; but `M52-gate-cluster-verified.md:670` already reported it, so the `M56 (MEASURED)` attribution is at best incomplete |
| 721 | `LADDERS` at `merge_cmd.rs:1934`; fact 627 does record `:1833` | **CONFIRMED** |

---

## 5. Omissions — what the sources contain and SYNTHESIS does not

*All MEASURED by reading each source end to end and grepping SYNTHESIS for the text.*

1. **M55 §5.6 consequence 2** — "The direction is corroborated (`S(canon) 0.976 > S(old)
   0.936` in my harness at REPS = 8), **but the magnitude is not measurable**." The
   corroboration half is absent from fact 695 and from fact 640's amendment. *This
   omission runs in favour of the refutation being folded*, which is the direction a fold
   should be most careful about.
2. **M55 §5.6 consequence 3** — "**Every separation number in this corpus quoted to three
   figures is over-precise** — 0.937, 0.917, 0.990, 0.931, 0.973, 0.995, 0.994, 0.936,
   0.982, and my own 0.523 and 0.464." The word "over-precise" appears nowhere in
   SYNTHESIS, and 0.917 / 0.990 / 0.931 / 0.973 still stand unqualified inside facts 619
   and 622.
3. **M54 §5 item 3** — "`CTRL-bright` had only **22-107 px** on `coffee-bubbles` — **a rule
   36 failure**, caught by asserting the population size. It needed `coffee-bean`
   (2,430,956 px) to have any power at all." A self-reported failure of one of M54's own
   controls. Not in SYNTHESIS.
4. **M54 §9 decoder note** — "all percentages here use the `rawler` count, which is what
   the shipped pipeline sees." Question 161 carries the disagreement but not the fact that
   M54's own published percentages are on one side of it, which is the actionable half.
5. **M48b L88** — the `rho` uncertainty is "**±30% at ISO >= 1000 and ~±1% at ISO <= 100**,
   dominated by systematics". The ISO-dependence of the error bar is not in facts 663-678.
6. **M48b L230** — the omitted term is "**~200x smaller than the model's own provenance
   uncertainty**. This is a *positive* [result]". SYNTHESIS carries the 0.026% but not the
   200x framing that makes it a confirmation rather than a small error.

**Source-level errors the fold carried across faithfully** (attribute to the source, not to
the folder): M48b local fact 8's headline says "0.05% of the lit frame's **total** variance"
where its own bullet says "**non-FPN** variance" (SYNTHESIS 670 took the headline); M48b
local fact 11's "two to three orders of magnitude" against an attenuation table whose low
end is 52x, ~1.7 orders (SYNTHESIS 673).

**A point in the folder's favour, MEASURED:** M54 §1's headline says "99.6%" never-clipped
where §3's table says 94.9 / 81.8 / 98.7%. The fold used **the table** (fact 684:
"81.8-98.7%"), not the headline. That is the correct behaviour and it is the opposite of
the failure mode this audit was commissioned to look for.

---

## 6. Structural integrity — independently verified, at `9aca35f`

Checked with my own scripts, not the folder's. **MEASURED:**

```
bytes=648297  ends in exactly one LF  no CRLF anywhere
section starts: 1:40 2:138 3:157 4:711 5:1331 6:2242 7:2275 8:2414 9:2561 10:2629
fact rows=516  distinct=516  bad_pipe_rows=0
duplicate fact numbers: {}          fact range 1..725   missing in 663-725: none
disciplines=182  max=347  dups: none  missing in 329-347: none
questions=108    max=171  dups: none  missing in 155-171: none
facts-range numbers living in section 5: none
indent-after-blank candidates: 2 (both pre-existing blockquote continuations at 1541, 1549)
```

Pipe rule used: a §4 fact row must contain exactly **5** unescaped `|` after removing `\|`;
the `### 4.1` three-column sub-table is excluded. **MEASURED history:** at `606c8f7` and
`d7eedfa`, rows **617, 621, 624** each had 7 unescaped pipes and were rendering with the
Source column dropped; repaired at `7ebfdfa`. `d7eedfa` did not end in a newline; repaired
at `7ebfdfa`. Row counts across the session: 453 -> 470 -> 485 -> 503 -> 514 -> 515 -> 516.

**Nothing severed, nothing orphaned, nothing in the wrong section, no number reused.** All
four self-reported defect classes are genuinely fixed and stayed fixed.

---

## 7. OWNER-QUESTIONS items 32-38

**Well-supported, MEASURED against M55.** Item 35's numbers all check out: non-monotone
above ~0.7 px (M55 L84), 344x past threshold (L238, L496), 0.15% saturates / real merges
differ by ~12% / 83x (L252-257), 50x and 1751x (§5.5), "0.37 to 0.74 where it needs above
0.90" (§5.4), "on the very region its author tuned it on, the improved version is worse"
(§5.4). Item 36's counts match fact 713 (260 / 18 / 11, five user-visible). Item 33's
"passes for any value between 0.02 and 3.0" matches fact 697 exactly. Item 37's "agree to
1.4%" is **DERIVED-correct**: 0.2888 / 0.2849 = 1.0137.

**Findings:**

- **Item 36, "Every single run prints a citation to 'fact 200a'"** — overstated; see L4.
  The string is in one `match` arm.
- **Item 32, "the verifier attacking it reported two critical defects on real data"** — the
  first of the two (non-monotonicity) was measured on a **synthetic ladder**, which the same
  paragraph then says ("on a controlled ladder it reads 2.03x its baseline"). Only the
  second is on real data.
- **Item 32, "Three further defects … are individually fixable; the first two are not."**
  The antecedent of "the first two" is the two critical defects two paragraphs up, not the
  three just listed. On a phone, the sentence reads as self-contradictory. This is a
  correctness risk in a file written for a non-specialist, not a style point.
- **Item 38 is honest, and errs against itself.** It states the override in a bolded
  heading ("**Where I am overruling my own pre-commitment, stated plainly so you can
  overrule me back**"), says "I did start a fourth hunt", gives one ground, states the
  bound, concedes "a real possibility I cannot rule out from the inside", and offers to
  stop at no cost. Its one inaccuracy — paraphrasing "a fourth is not obviously repayable"
  as "**do not start a fourth hunt for a metric**" — makes the pre-commitment sound *more*
  binding than it was, i.e. makes the override look worse. **ARGUED: this is not
  self-serving.** The self-serving rendering is in fact 724, which trims the same clause
  out of its quotation (L5).

Nothing in items 32-38 understates a bad result. Item 33's "nothing shipped" and item 35's
"nothing shipped and nothing is lost but a claim" are both **MEASURED-true** — no binary
consumes `sigpow`.

---

## 8. What I could not check

- **Facts 713-723** against a source report: there is none (§4).
- Whether the M56 experiment artefacts in the untracked `experiments/M56-citations/`
  support the rows: out of scope for a fidelity audit, and untracked material can change
  under me.
- Whether M48b and M55 were run on "different nights" (OWNER-QUESTIONS item 37): both were
  folded in one session and I have no timestamp evidence either way.
- Facts 202, 203, 242 were re-read in full; 242's amendment sits in the Fact column of a row
  whose Source column says "**Do not cite this row**", which is confusing but not false.
- Four other agents were live in the repository during this audit; HEAD moved from `9aca35f`
  to `9f6db3a` while I worked. All structural counts above are pinned to `9aca35f`, the last
  audited commit that touches SYNTHESIS.

---

## 9. Summary table, ordered by severity

| # | Finding | Class | Sev |
|---|---|---|---|
| H1 | Fact 725 says 7 rows and lists 8; fact 613 named, never amended, now internally false | structural | HIGH |
| H2 | Fact 610 never amended for fact 697; still claims a 0.4% out-of-sample confirmation | omitted amendment | HIGH |
| H3 | Fact 202's "absent from four of six stacks" contradicted by its own amendment | unsupported amendment | HIGH |
| M1 | "Four of the six failing cells are flat" (707, q165) — not in source, false on its table | transcription | MOD |
| M2 | Fact 696 "four of six below 0.5" — three are | transcription | MOD |
| M3 | Fact 627 cites fact 723 for an ISO claim 723 does not contain | citation | MOD |
| M4 | Facts 717 and 719 contradict on `profile.rs:92`; "all cite fact 200" is false | transcription | MOD |
| M5 | Fact 622 repaired in the headline, not in the Consequence | structural | MOD |
| M6 | Fact 694 "two of them" is one; row 620's provenance silently rewritten | transcription | MOD |
| M7 | Fact 688 / discipline 333 drop the `coffee-bubbles` scope on 1.023 / 97.7% | transcription | MOD |
| M8 | Fact 709 says two self-refutations; source says three | transcription | MOD |
| P1 | M56 fold has no committed source report; rule 31 | process | MOD |
| L1 | `S` range 0.770-0.976 vs source 0.770-0.980, in four places | transcription | LOW |
| L2 | Fact 708 pairs mismatched adversaries | transcription | LOW |
| L3 | Fact 673 attributes 132 DN to fact 655, which lacks it | citation | LOW |
| L4 | "every run" overstated in 717 and OQ 36 | transcription | LOW |
| L5 | Fact 724 trims the violated clause out of its quotation | omission | LOW |
| L6 | Fact 689's "nearly three orders" unsupported, mixed denominators | transcription | LOW |
| L7 | Fact 676 misattributes question 20's hypothesis; q20 is closed | unsupported amendment | LOW |
| L8 | Fact 681 drops `coffee-bean` scope | transcription | LOW |
| L9 | Discipline 340 cites itself | citation | LOW |
| L10 | `d7eedfa` message says two deletions; there are three | process | LOW |
| L11 | Question 142's continuation indented 1 space, not 5 | structural | LOW |
| L12 | Fact 612 not rescoped though M55 §2.4 refutes its amplitude | omitted amendment | LOW |
| O1-O6 | Six omissions from M55 / M54 / M48b (§5) | omission | LOW-MOD |
| OQ | Items 32/36 overstatements; item 38 judged honest and self-incriminating | — | LOW |

**Six of the twenty-five findings are in the M56 fold, which is also the one fold with no
committed source. ARGUED: that correlation is the most actionable thing in this report.**
