# M56 — citation-content audit

**Recovered from the auditing agent's context on 2026-08-23, after the fold discovered
the report had never been committed. This replaces the disclosure stub at this path.**

**Audited commit: `d7eedfa`.** The binary all runtime measurements were taken with was
built at **`90e7db5`**; the only committed change to `crates/` between those two that
touches anything measured here is `53d06f5` (see U6). The tree moved six times during the
audit: `cc84514` -> `4a5c270` -> `90e7db5` -> `53d06f5` -> `606c8f7` -> `d7eedfa`.

**Line numbers in this repository rot.** They are given only as a hint. Every finding is
also identified by symbol name and by quoted content, which is the form that survives.

## 0. How to read the labels

Every claim below carries one of:

- **MEASURED** — I ran a command and read its output. The command is in section 2.
- **DERIVED** — arithmetic or a mechanical replication of shipped code on measured inputs.
- **ARGUED** — a reading of two documents against each other, with no number behind it.
- **UNRECOVERABLE** — I reported it, I no longer hold the evidence, and I will not
  reconstruct it.

Where the fold's row and my evidence disagree, the disagreement is stated rather than
smoothed. Three of the eleven folded rows are corrected below and I concur with all three
corrections; one of them is a real error in my instrument and is recorded as such in
section 9.

## 1. Scope and instrument

**The question.** Not "does every cited fact number resolve to a real section 4 row" —
M49 asked that and it is discipline 303's worthless check. The question was: **does the
row say what the citing code claims, and is any measured number quoted alongside it still
true of the pipeline today.**

**Inventory (MEASURED, `experiments/M56-citations/extract.py`).**
**260 citation instances, 77 distinct section 4 fact numbers, 18 files.** All 77 resolve
to a real row, so M49's instrument returns CLEAN on this same corpus a second time.

M49 reported **58** distinct numbers. I did not determine whether M49 under-enumerated or
the crates gained 19 numbers in the interval. **UNRESOLVED**, and worth resolving, because
the answer decides whether citation density is outrunning the checking.

**Corpus index (MEASURED, `parse_facts.py`, `parse_dq.py`).** Section 4 holds **453 rows
numbered 1-662** with 209 gaps and no duplicates; section 5 holds 167 disciplines to 328;
section 10 holds 87 questions to 150.

**The four verdicts used.** MATCHES / WRONG TARGET / STALE NUMBER / UNCHECKABLE.

## 2. Commands run

PATH prefix for every cargo invocation:
`$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"`. No `-q` anywhere.

```
cargo build --release
  -> Compiling strehl-core / strehl-plugin / strehl-raw / strehl-cli; Finished in 31.49s

cargo test --workspace --release
  -> Compiling strehl-core v0.0.0 ... Compiling strehl-cli v0.0.0
  -> 38 passed; 126 passed; 33 passed; 8 passed; 1 doc-test passed. 0 failed. 206 total.

cargo test --release -p strehl-cli fact_324 -- --exact \
    merge_cmd::tests::the_solved_gate_spans_the_range_fact_324_claims
  -> test ... the_solved_gate_spans_the_range_fact_324_claims ... ok
  -> test result: ok. 1 passed; 0 failed

cargo run --release -p strehl-plugin --example f5-design-probes
cargo run --release -p strehl-plugin --example calibration-survey

strehl.exe stack C:\dev\macro\test\109MSDCF -o <scratch>.tif --flat-roi 2272,1344,256,256

strehl.exe merge C:\dev\macro\test\109MSDCF \
    --flat-roi 2272,1344,256,256 --detail-roi 1630,1044,256,256 \
    --gate 0.5 --gate 1 --gate 2 --gate 4
strehl.exe merge C:\dev\macro\test\119MSDCF \
    --flat-roi 2896,1968,256,256 --detail-roi 2016,1152,256,256 \
    --gate 0.5 --gate 1 --gate 2 --gate 4
   (and the same two stacks again at --gate 0)

strehl.exe merge C:\dev\macro\test\109MSDCF --gate 0.15 --gate 0.1512 --gate 0.168 \
    --gate 0.1684 --gate 1.0
strehl.exe merge C:\dev\macro\test\109MSDCF --gate 1 --stats
strehl.exe merge C:\dev\macro\test\109MSDCF --gate 1 --stats --stats-placebo
strehl.exe merge D:\personal\macro\foam --gate 4 --gate 8 --gate 16 --gate 24 --gate 32 \
    --target-n-eff 3
strehl.exe merge C:\dev\macro\test\119MSDCF --flat-roi 3056,416,256,256 --gate 1

  plus a full default gate sweep (0.5/1/2/4) on all seven corpus stacks:
  119MSDCF(33,ISO50) 109MSDCF(22,ISO160) 113MSDCF(63,ISO500) 112MSDCF(79,ISO500)
  coffee-bean(105,ISO50) coffee-bubbles(19,ISO1000) foam(100,ISO1000)

strehl.exe merge --help ; strehl.exe stack --help ; strehl.exe --help
```

ROI coordinates are M18's canonical pairs (`M18-merge-implemented.md` sections for each
stack); `3056,416` is fact 441's own 119MSDCF ROI.

Scripts and captured output are under `experiments/M56-citations/`, committed. The two
highest-value artefacts are `raw_fact_lines.txt` (all 257 raw citation lines with
`file:line` and quoted content) and `join_b.txt` (each cited fact's **full section 4 row
text joined to the code lines that cite it**) — the latter is the actual instrument of a
content audit, and both of my counting errors in section 9 would have died on contact
with it.

**Two files are deliberately not committed.** `facts.json` (370 KB) and `disc_ques.json`
(150 KB) are large mechanical re-serialisations of SYNTHESIS sections 4, 5 and 10; the
corpus state they pin is recoverable exactly with
`git show d7eedfa:docs/research/SYNTHESIS.md` plus the committed `parse_facts.py` and
`parse_dq.py`, and every cited row's text is already quoted inline in `join_b.txt`. They
are redundant, not lost.

**The directory was deliberately not renamed to `experiments/m56-citation-audit/`.** It is
already a milestone directory with 11 files tracked in it, and the path
`experiments/M56-citations/` is referenced from five files this audit may not edit —
including **`SYNTHESIS.md`'s fact 765, the row that exists to record this very rule-31
violation** — and hardcoded inside three tracked scripts (`ctx.py`, `extract.py`,
`group.py`). Renaming would break fact 765's own evidence pointer.

## 3. Confirmations and corrections of facts 713-723

The orchestrator supplied the substance of eight of the eleven rows. Those eight are
answered here. **Rows 714, 718 and 720 were not quoted to me and I have not seen their
text. I will not confirm rows I cannot read.** Section 3.9 says what I can offer instead.

### 3.1 Row 713 — the two instruments are different — CONFIRM, with the headline count corrected

**MEASURED.** M49's instrument (does the number resolve) returns CLEAN on my inventory
too: 77 of 77 resolve. My instrument (does the row support the claim) returns defects on
the same set. The distinction is real and it is the whole finding.

**CORRECTION to my own headline.** I wrote "11 citation-content defects, 5 of them
user-visible". **The 5 is exact and enumerable** (U1-U5 in section 4; U6 was fixed by
another agent mid-audit and is not mine). **The 11 was not rigorously derived.** The
defensible breakdown, which I should have given instead of a round number, is:

| Class | Count | Which |
| --- | --- | --- |
| WRONG TARGET — code asserts something the row does not say | 5 | U1, U2 (x2 sites), D2 (x3 sites), D6, D8 |
| STALE NUMBER — number quoted was true once, is not true now | 4 | U5, D1, D3, D4 |
| DANGLING — citation names something that is not a fact | 2 | U4, D2's `200a` site |
| UNDEFENDED — citation true but a later row scopes it, unnoted | 3 | U3/D5 (fact 580), D7 (fact 439), fact 505's five sites |

Fourteen findings if counted one per finding; eleven if the three multi-site findings are
counted once each and U6 excluded. **My "11" was the second counting and I did not say
so.** DERIVED.

### 3.2 Row 715 — fact 505's figure is quoted at five sites — CONFIRM (exact)

**MEASURED.** Fact 505's row states its own figure must not be quoted. It is quoted at
five sites, identified by symbol:

| Site | Quoted content |
| --- | --- |
| `strehl-plugin/examples/f5-design-probes.rs`, PROBE 3 `println!` | the per-plane cost line |
| `strehl-plugin/src/calibrate.rs`, module `# Cost` header | " |
| `strehl-plugin/src/calibrate.rs`, `CalibrationPlan::host_default` doc | " |
| `strehl-plugin/src/lib.rs`, module header | " |
| `strehl-plugin/src/measure.rs`, `Window::Custom` doc | " |

The aggravating detail the row captures correctly: **one of the five is a `println!` in
the example whose own output refutes the figure.** MEASURED, `cargo run --release -p
strehl-plugin --example f5-design-probes`: PROBE 3 reports tenengrad **59.84 ms / 12
seeds = 4.99 ms per plane** and sml **63.23 ms = 5.27 ms per plane**. Fact 525's 5.02 ms
and 60.3 ms reproduce; **fact 505's ~1.7 ms is 2.9x low** and the program prints the
refutation next to the citation.

### 3.3 Row 716 — fact 580's park outlived its condition — CONFIRM, plus a detail

**ARGUED, on the text of fact 580 and the presence of M52's report.** Fact 580 parked five
sites "pending M52". M52 landed. The park did not lift. A reader now reads it as a
decision rather than as a wait, which is the defect.

**Detail the row may not carry (MEASURED): two of the five parked sites are user-visible
under `--stats`** — they are printed, not just documented. That raises the finding from a
doc-comment staleness to something a user reads. This is U3/D5 in section 4.

### 3.4 Row 717 — `stack.rs` prints "fact 200a" — CONFIRM, and **the later scoping is correct**

**MEASURED at `d7eedfa`:**

```
git show d7eedfa:crates/strehl-cli/src/stack.rs | Select-String 'fn provenance_line|Provenance::(Profile|Measured|Fallback) =>|200a'
  pub(crate) fn provenance_line(noise: &NoiseModel) -> String {
  // twice, independently" + fact 200a's unlocated boundary), and
  Provenance::Profile => format!(
      "200a -- the corpus\n",
  Provenance::Measured => format!(
  Provenance::Fallback => concat!(
```

**The string literal sits inside the `Provenance::Profile` arm only.** The `Measured` and
`Fallback` arms contain no such string. **"On every run" is an overstatement and the later
audit is right to narrow it.** The accurate statement is: *`provenance_line`'s
`Provenance::Profile` arm prints `200a`, so it prints on every run whose camera matches a
shipped profile.* For this project's corpus that is every run — all seven stacks are
ILCE-7CM2 and every run I captured printed it — but the code has two other arms and the
row should not have claimed the arm-independent form.

`200a` is not a fact. It exists only as a report-local sub-item at
`M25-simulator-measured.md:858` (`**200a. OPEN -- the boundary is not measured.**`), folded
as **question 126**. A user is told to consult a fact number that does not exist.

The same dangling `200a` appears at two further sites: **`stack.rs`'s comment above
`provenance_line`** and **`profile.rs`'s `read_noise_e_low` doc** (section 3.5).

### 3.5 Row 719 — `profile.rs` line rot — CONFIRM the rot, and **the accompanying claim is false; the later audit is right**

**MEASURED at `d7eedfa`:**

```
git show d7eedfa:crates/strehl-core/src/profile.rs | Select-String 'M25 fact'
  72: /// **MEASURED at ISO 160, by photon transfer on signal** (M25 fact 200):
  87: /// 1.0021 where a genuine gain step demands 0.5. M25 fact 200 from signal,
  92: /// **The boundary itself is not measured** (M25 fact 200a): the corpus holds
 112: /// corpus's real stacks are ISO 50 and ISO 160 (M25 fact 200's table).
```

Fact 581 recorded these at `:25, :40, :45`. **Line rot CONFIRMED**: they are at
`:72, :87, :92, :112`, and there are four of them where fact 581 named three.

**But "all four cite `M25 fact 200`" is FALSE, and it is my error.** `:92` cites
**`M25 fact 200a`**. My grep pattern was the substring `M25 fact`, which cannot
distinguish `200` from `200a`, and I wrote the count from the match tally rather than from
the four quoted lines — which I had, and which are printed above.

**These are two different defects, not four instances of one:**

- `:72`, `:87`, `:112` (in the `gain_divisor` and `base_iso` field docs) are **fact 581's
  WRONG TARGET shape**: `M25 fact 200` resolves as if it were section 4 fact 200, which is
  M26's white-balance row; M25's report-local fact 200 was folded as section 4 fact
  **550**. Because `profile.rs` is about white balance *and* gain, the wrong reading is
  locally plausible. **Three sites.**
- `:92` (the `read_noise_e_low` field doc) is the **DANGLING shape**, the same defect as
  row 717: `200a` is not a fact at all. **One site.**

Fact 581 was fixed nowhere; both shapes were live at `d7eedfa`.

The discipline this produced — **cite by symbol name or quoted content, never by line
number** — is the one I then failed to apply to my own prose. See section 9.

### 3.6 Row 721 — `LADDERS` line rot — CONFIRM (exact)

**MEASURED.** `const LADDERS: [(&str, [(f64, f64); 4]); 5]` in `merge_cmd.rs`'s
`mod tests` begins at **line 1934** at `d7eedfa`, not `:1833`.

### 3.7 Row 722 — `reference.rs` pairs one operator's gate with another's pixel fraction — CONFIRM, and **the later resolution is exactly right**

**MEASURED**, `strehl merge C:\dev\macro\test\109MSDCF --gate 0.15 --gate 0.168 --gate 1.0`:

| gate | mean `n_eff` | fraction of pixels at `n_eff` = 1 |
| --- | --- | --- |
| 0.150 | 1.117 | **89.02%** |
| 0.168 | 1.131 | **87.76%** |
| 1.00 | 1.884 | 41.66% (fact 458 reproduces exactly) |

Both numbers in the citing sentence trace to real rows and **both re-measure exactly**.
The sentence is false only because it **pairs the gate from one operator's row with the
pixel fraction from another's**. This is the most instructive defect in the audit: no
number in it is wrong, no citation in it fails to resolve, and M49's instrument and a
naive re-measurement instrument both return CLEAN. Only reading the sentence catches it.

### 3.8 Row 723 — the fact 439 enumeration — **my row over-counts 4x and under-counts at the same time; the later audit is right**

I listed eight sites (`lib.rs:16`, `reference.rs:1, 16, 25, 213, 259, 308, 420`) as
quoting fact 439's `10.4x` span. **MEASURED at `d7eedfa`**, that grouping is wrong in both
directions:

**Sites that actually quote the literal span — TWO, not eight:**

| Symbol | Quoted content |
| --- | --- |
| `strehl-plugin/src/lib.rs`, module header | "**10.4x** (fact 439: ring(1,3) 0.644 to sum-modified-Laplacian 6.680)" |
| `strehl-plugin/src/reference.rs`, module header | "They let fact 439's 10.4x spread be reproduced *inside the crate*" |

These two, and only these two, are scoped by fact 635.

**Sites that quote a single operator's `k`** — fact 635 changes the *span* under a
consistent window convention and leaves the individual operators otherwise unchanged, so
**these are not affected by it at all** and my listing them was wrong:

| Symbol | Quoted content |
| --- | --- |
| `reference.rs`, `Laplacian` doc | "Fact 439 puts it at `k` = 6.590" |
| `reference.rs`, `SumModifiedLaplacian` doc | "fact 439 measures it at `k` = 6.680" |
| `reference.rs`, `RingDifference` doc | "the low end of fact 439's spread at `k` = 0.644" |
| `reference.rs`, module header | "the *other* end of fact 439's spread ... erring at `k` = 0.644" |

**Sites quoting `6.680` that I never named — THREE:**

| Symbol | Quoted content | Visible? |
| --- | --- | --- |
| `calibrate.rs`, survey test `println!` | "sml k = {:.4} (fact 439: 6.680) tenengrad-sq k = {:.4} (fact 439: 1.367)" | test stdout |
| `calibrate.rs`, survey test assertions | "SML must land near fact 439's 6.680" / "tenengrad-squared must land near fact 439's 1.367" | assert msg |
| `registry.rs`, fault-5 test `println!` | "host's {FOCUS_NOISE_SD:e} (fact 439 measures 6.680)" | test stdout |

**Sites naming fact 439 with no number, which belong in neither list:** `lib.rs`'s
`reference` module list entry, `reference.rs`'s `all_operators` doc ("in the order the
fact lists them"), `reference.rs`'s comparability note, `calibrate.rs`'s `FOCUS_NOISE_SD`
doc, `registry.rs`'s mis-matched-operator doc, `measure.rs` (two sites), and `field.rs`
("not expected to match fact 439 to the last digit" — which is the *correct* hedge and
should be the model for the others).

**Root cause, same as 3.5:** my grouping index was keyed on `(fact number, file)`, and I
wrote the prose from the grouping instead of from the quoted lines. **A number-keyed index
cannot tell you what a site says.** That is discipline 303 turned one level inward, onto
my own instrument, and it is the single most useful thing this recovery has produced.

### 3.9 Rows 714, 718, 720 — **UNRECOVERABLE as confirmations**

Their text was not quoted to me. I will not confirm rows I have not read, and I will not
guess which of my findings each one folded. What I can do is state my findings in full in
section 4 and let the fold match them; **U1, U5 and D3 are the three findings most likely
to be behind these rows**, and each is stated there with its own independent evidence, so
each is checkable on its own terms whether or not the match is right.

## 4. The findings

Ranked by whether a user can see them, then by whether the code is wrong now versus merely
undefended. All at `d7eedfa`, cited by symbol.

### 4.1 USER-VISIBLE — a user reads these without opening the corpus

#### U1 — `merge_cmd.rs` attributes fact 23's regularised speckle to the wrong operator, in printed output. **Highest severity in the audit.**

**The site.** `merge_cmd.rs`, the speckle-companion `eprintln!` that accompanies the
speckle report. Quoted content:

> "Fact 23's reference points are 34.4% (ring operator, unregularised) and 0.868%
> (**Tenengrad**, regularised)."

**Why it is wrong (MEASURED).** `0.868%` is the **ring difference** regularised, not
Tenengrad. Source: `M2-verification.md:150-154`, the table row
*"regularised — argmax of a 17x17-smoothed focus field | **0.868%**"*, and `:205`,
*"the ring-difference focus measure correlates winners over 3-7 px"* — the whole M2
section is about the ring operator. Fact 71 records that swapping ring to Tenengrad on the
same ROI moves speckle **34.381% -> 1.010%**; fact 343 records that *"fact 19's 1.253x
does not reproduce on the shipped operator"* for exactly this reason.

**What the shipped pipeline actually produces (MEASURED):**

| Quantity | Value | Where |
| --- | --- | --- |
| Tenengrad, **unregularised** | **1.010%** | `strehl stack 109MSDCF`, index speckle |
| Tenengrad, **regularised** (the quantity the string claims to describe) | **0.022%** (109MSDCF), **0.025%** (119MSDCF) | `strehl merge` speckle line |
| what the string tells the user | 0.868% | the `eprintln!` |

**The printed "reference" is 39x the value the program printed one line earlier.** No
section 4 row publishes a regularised-Tenengrad speckle at all, so the string invents a
reference point and attributes it to a fact.

**CORRECTED 2026-08-23, from this audit's own committed evidence, for routing.** The
original text of this finding named a second site as "`strehl-core/src/stack.rs`, the
`DEFAULT_SPECKLE_TOLERANCE` doc comment". **The symbol name is not supported by any
captured evidence** — `DEFAULT_SPECKLE_TOLERANCE` appears in none of the context dumps —
and re-reading `join_a.txt` and `raw_fact_lines.txt` shows the finding was both
mis-stated and under-enumerated. The accurate statement:

**Fact 23's row names no operator at all.** Its text (`join_a.txt:37`) is:

> "Regularising the focus field (17x17 smooth) before argmax drops speckle
> **34.4% -> 0.868%** and noise **1.253x -> 1.075x**"

So the defect is *not* that code quotes fact 23. It is that **two sites add an operator
attribution the row does not contain, and pick the wrong operator**, while **two sibling
sites quote the same row operator-neutrally and are correct**:

| Site | Crate | Quoted content | Verdict |
| --- | --- | --- | --- |
| `strehl-cli/src/merge_cmd.rs:1281`, the speckle-companion `eprintln!` | **strehl-cli** | `"detail move it away from that. Fact 23's reference points are 34.4% \` ... rendering at runtime as *"34.4% (ring operator, unregularised) and 0.868% (Tenengrad, regularised)"* | **WRONG, user-visible** |
| `strehl-core/src/stack.rs:175` | **strehl-core** | `/// Fact 23's reference points are all at this tolerance: 34.4% for the ring` | **WRONG** — same invented attribution. Anchor on this quoted line; the enclosing symbol name is **unverified**. |
| `strehl-cli/src/merge_cmd.rs:16`, module header | strehl-cli | `//! over the focus field drops winner-index speckle from 34.4% to 0.868%` | **CORRECT — do not edit** |
| `strehl-core/src/merge.rs:196` | strehl-core | `/// 34.4% to 0.868% (fact 23), and speckle *is* the winner's curse made visible.` | **CORRECT — do not edit** |

**The repair spans two crates and therefore two owners**, and two of the four sites must be
left alone. Runtime rendering of the wrong string is captured verbatim at
`roi_109.txt:166-167`, `roi_119.txt:166-167`, `roi_109_g0.txt:154-155` and
`roi_119_g0.txt:154-155`.

**This is a fifth error by this audit** and it is the same error as the other two: I named
a symbol from memory instead of from the captured line, and I enumerated from a grouping
instead of from the evidence, so I missed the two correct sites that make the defect
legible. See section 9.

**Aggravating.** The same file states the identical operator caveat **correctly** for fact
19 about 210 lines earlier: *"Fact 19's 1.253x was a DIFFERENT focus operator and does not
reproduce here."* The author knew the distinction, applied it once, and did not apply it
to the adjacent row. **This is the shape to look for elsewhere: a caveat present in one
place and absent from its sibling.**

Verdict: **WRONG TARGET, user-visible, wrong today.**

#### U2 — the same mis-attribution reaches the user through two independent strings

Counted separately from U1 because they are two edits, not one: the `merge_cmd.rs`
`eprintln!` and the `strehl-core/src/stack.rs` `DEFAULT_SPECKLE_TOLERANCE` doc. Fixing one
leaves the other. **WRONG TARGET.**

#### U3 — two of fact 580's five parked sites are printed under `--stats`

**MEASURED**, `strehl merge ... --gate 1 --stats`. The park text ("pending M52") is in
output a user sees, and M52 has landed. **UNDEFENDED, user-visible.** See also D5.

#### U4 — `provenance_line` prints "fact 200a", which is not a fact

Full evidence in section 3.4. **DANGLING, user-visible**, on every run whose camera
matches a shipped profile — which was every run in the corpus.

#### U5 — `--stats` help says 494 MB per worker; the same binary in the same run prints 527 MB

**MEASURED.** `strehl merge --help` renders the clap help for `--stats`:

> "it costs **494 MB per worker**"

`strehl merge C:\dev\macro\test\109MSDCF --gate 1 --stats` prints, in the same execution:

> "of which stats: **527 MB/worker**"

**Cause (DERIVED, from the shipped arithmetic).** `merge_cmd.rs` has
`const FINE_FIELD_PER_PX: usize = 4;` and computes
`stats_bytes = px * (FINE_FIELD_PER_PX + gathers * ThroughFocus::bytes_per_pixel())`.
**60 bytes per pixel is correct for the struct.** "494 MB per worker" is not correct for
the option as shipped. The help text and the runtime report disagree by **6.7%**, and the
help text is the one the user reads before deciding whether they can afford the flag.

Verdict: **STALE NUMBER, user-visible, wrong today, self-refuting within one run.**

#### U6 — NOT MY FINDING, recorded to prevent mis-attribution

The `50.9-90.0%` -> `50.9-80.0%` correction (fact 597) landed in **`53d06f5`, by another
agent, while my audit was running.** I found it independently and briefly recorded it as
an M56 finding before checking the log. **It is not mine and must not be folded as mine.**

### 4.2 NOT USER-VISIBLE, BUT WRONG TODAY

#### D1 — `MergeOptions::target_n_eff`'s doc still carries fact 324's superseded ladder

**MEASURED.** The doc comment on `MergeOptions::target_n_eff` in `merge_cmd.rs` reads:

> "at gate 2.0 mean `n_eff` runs 2.26 to 7.42 across five stacks, and the gate needed to
> reach `n_eff = 3` runs 1.1 to 2.9."

This is **the same sentence fact 627 named two days earlier** and that commit `1980538`
fixed in the CLI help. **The doc-comment copy was not fixed and was still live at
`d7eedfa`.** The true seven-stack range measured today is **1.177 to 14.386** at gate 2.0
and **0.762 to 21.993** for the gate solving `n_eff = 3`.

Verdict: **STALE NUMBER.** The lesson is that fixing the user-visible instance of a
duplicated wrong number does not fix the duplicate.

#### D2 — `profile.rs`'s four mis-cited sites

Full evidence in section 3.5: three WRONG TARGET (`M25 fact 200` -> section 4 fact 550,
not fact 200), one DANGLING (`M25 fact 200a`). Fact 581 named this and it is unfixed.

#### D3 — `the_solved_gate_spans_the_range_fact_324_claims` is GREEN and two of its three assertions are false of the current pipeline

**MEASURED and DERIVED.** The test in `merge_cmd.rs`'s `mod tests` runs
`solve_gate_for_n_eff` against the frozen `LADDERS` fixture, not against the pipeline. I
replicated the shipped log-log interpolation in `experiments/M56-citations/solve_check.py`
and ran it on both the fixture and on ladders measured today:

| Input | lo | hi | hi/lo | `lo in [1.0,1.2)` | `hi in [2.7,3.1)` | `hi/lo > 2.4` |
| --- | --- | --- | --- | --- | --- | --- |
| frozen `LADDERS` (what the green test runs on) | 1.1064 | 3.0111 | 2.7215 | true | true | true |
| today, same five stacks | 0.7618 | 2.1486 | 2.8206 | **FALSE** | **FALSE** | true |
| today, all seven stacks | 0.7618 | 3.2144 | 4.2197 | **FALSE** | **FALSE** | true |

**Two of the three assertions are false of the pipeline the test claims to characterise.
The test is green because it asserts against the fixture.** This is AGENTS rule 35 /
discipline 316 exactly, and the test's name — `..._fact_324_claims` — promises the reader
it checks the claim.

Verdict: **STALE NUMBER, green-but-false.** Confirmed as the known instance from M52.

#### D4 — the `LADDERS` fixture is stale on 8 of its 20 rungs

**MEASURED**, seven-stack sweep at gates 0.5 / 1.0 / 2.0 / 4.0. Drift frozen -> today:

| stack | ISO | 0.5 | 1.0 | 2.0 | 4.0 |
| --- | --- | --- | --- | --- | --- |
| 119MSDCF | 50 | +9.73% | +17.33% | +26.09% | +29.26% |
| 109MSDCF | 160 | 0.00% | 0.00% | 0.00% | 0.00% |
| 113MSDCF | 500 | -0.07% | -0.18% | -0.27% | -0.10% |
| 112MSDCF | 500 | -0.19% | -0.43% | -0.58% | -0.23% |
| coffee-bean | 50 | +23.35% | +58.44% | **+93.83%** | +27.99% |

**Fact 627 names only the gate-2.0 value.** The staleness is not one number: it is **both
ISO-50 stacks on every rung**, which is the exact fingerprint of commit `2a4f5c5`'s
`max(iso, 100)` base-ISO floor. The ISO-160 stack is bit-identical and the ISO-500 stacks
moved under a quarter of a percent.

**This gives a cheap rule for triaging every other number in the corpus (DERIVED):** a
measurement taken before `2a4f5c5` is suspect **iff** it involves ISO < 100; a measurement
taken before `f95f6f4` (`read_noise_e_high` 1.47 -> 1.2392) is suspect **iff** it involves
ISO >= 400. Numbers from ISO 160 alone survive both.

#### D5 — fact 580's five parked sites, listed

**MEASURED.** Five sites carry the "pending M52" park; two are printed under `--stats`
(U3), three are doc comments. M52 landed; none were revisited. **UNDEFENDED.**

### 4.3 UNDEFENDED — citation true, but a later row scopes it and the code does not say so

#### D6 — fact 436's substitution is cited without fact 631's scoping

`strehl-plugin` cites fact 436 as if unqualified. **Facts 631 and 632 scope it.** The
plugin crate carries no note of either. **ARGUED**, on the text of the three rows.

#### D7 — fact 439's span, corrected

See section 3.8. **Two** sites quote the span and are scoped by fact 635; five quote an
individual `k` that fact 635 leaves untouched and are **not** defective; three quote
`6.680` and were never enumerated.

#### D8 — `TenengradSquared` states a plan that fact 662 has already invalidated. **The most consequential of the three.**

**MEASURED, quoted content.** `reference.rs`'s `TenengradSquared` doc says the operator
exists

> "so that the pending change can be calibrated before it lands".

**Fact 662 says the edit lands on the *core* path, and that `k = 1.5306` is the *wrong*
correction — change (c) must not be applied as specified.** A contributor who reads the
plugin doc and does the calibration it describes will do work fact 662 has already ruled
out, on the wrong crate.

Verdict: **WRONG TARGET.** A doc comment that instructs a reader to perform superseded
work is worse than one that merely records a stale number.

## 5. Frozen-fixture census (rule 35 / discipline 316) — **the brief's expectation is refuted**

The brief said "M52 believes there are more". **MEASURED: there is exactly one.**

I examined every test in the workspace that asserts against frozen measured data — seven
in total. **One is green-but-false. Six are correctly shaped.** The distinction that
separates them is worth stating because it is a design rule, not a code-review taste:

| Test | Shape | Verdict |
| --- | --- | --- |
| `the_solved_gate_spans_the_range_fact_324_claims` (`merge_cmd.rs`) | asserts a *pipeline claim* against a frozen ladder | **GREEN-BUT-FALSE** (D3) |
| `a_gradient_increase_is_never_scored_as_a_pass` (`merge_cmd.rs`) | frozen readings feed a *pure threshold function*, `detail_verdict()` | **FRAGILE, not false** |
| plugin `calibration-survey` assertions (`calibrate.rs`) | **recomputes** `k` by running the operators, then compares to fact 439 with a tolerance | **CORRECT** |
| `registry.rs` fault-5 | recomputes, prints the comparison | **CORRECT** |
| three further fixture tests | fixtures are *inputs*, not *claims* | **CORRECT** |

**The rule that falls out (DERIVED):** a frozen fixture is safe when it is an **input** to
a function under test, and unsafe when it stands in for the **output of the pipeline the
test's name claims to characterise**. `detail_verdict()` is a pure function of its
argument, so freezing the argument tests the function honestly; `solve_gate_for_n_eff`
over `LADDERS` is not a test of the pipeline at all.

**Fragility measured, not assumed.** The frozen detail-retention readings
`[1.257, 1.254, 1.027, 1.021]` re-measure today as: 109MSDCF gate 0 -> **1.257** (exact),
109MSDCF gate 2.0 -> **1.254** (exact), 119MSDCF gate 2.0 -> **1.021** (exact), 119MSDCF
gate 0 -> **1.028** where the fixture says 1.027 (+0.1%). Since the test asserts only on
`detail_verdict()`, the drift does not flip any assertion. **FRAGILE, correctly reported
as such rather than inflated into a second defect.**

## 6. Corpus-row defect found while checking code against rows

#### C1 — fact 627's parenthetical names the wrong ISO

**MEASURED, from the binary's own stack headers.** Fact 627 says *"the three stacks that
reproduced are the **ISO-160** ones"*. There is **one** ISO-160 stack. The three that
reproduced are 109MSDCF (**ISO 160**), 113MSDCF (**ISO 500**) and 112MSDCF (**ISO 500**).

The finding survives the correction and is in fact strengthened by it: what the three have
in common is **ISO >= 100**, i.e. they are the stacks the `max(iso, 100)` floor of
`2a4f5c5` did not move. Reading "ISO-160" instead of "ISO >= 100" hides the mechanism.

**This is a defect in section 4, not in `crates/`.** I report it here because the code
audit is what surfaced it.

## 7. Citations checked and CONFIRMED CORRECT by re-measurement

Recorded because a defect list without its denominator is not evidence, and because these
are the rows a future audit does not need to re-run.

| Row | Claim | Re-measured today |
| --- | --- | --- |
| 71 | ring -> Tenengrad moves speckle to ~1.010% | **exact**: stacked sd 30.114, single-frame sd 28.201, ratio 1.068x, 6 distinct winners, speckle **1.010%** |
| 343 | shipped operator gives 1.0739x | **1.074x** |
| 424 | 78.081% | **exact** |
| 458 | 41.66% at gate 1.0 | **exact** |
| 525 | 5.02 ms/plane, 60.3 ms total | **4.99 / 59.84** — reproduces |
| 439 | seven operators, per-operator `k` | ring-1-3 **0.6437** (0.644), tenengrad **0.9998** (1.008), tenengrad-sq **1.3592** (1.367), brenner **1.9694** (1.962), local-variance **2.4806** (2.475), laplacian **6.5235** (6.590), sml **6.6118** (6.680); span today **10.27x** vs 10.4x published |
| 441 | 1.5989 raw-sd flat ratio, ROI `3056,416` | reproduces **as a raw-sd statistic** — see error 2 in section 9 |

Full seven-stack gate ladder measured today (mean `n_eff` at 0.5 / 1.0 / 2.0 / 4.0, then
the gate solving `n_eff = 3`):

```
119MSDCF      (33 fr, ISO   50)  1.399 / 1.855 /  2.847 /  4.723  -> 2.1486
109MSDCF      (22 fr, ISO  160)  1.414 / 1.884 /  2.891 /  4.987  -> 2.0963
113MSDCF      (63 fr, ISO  500)  1.432 / 2.194 /  4.761 /  8.581  -> 1.3230
112MSDCF      (79 fr, ISO  500)  1.551 / 2.561 /  6.190 / 12.037  -> 1.1323
coffee-bean  (105 fr, ISO   50)  1.870 / 4.072 / 14.386 / 31.614  -> 0.7618
coffee-bubbles(19 fr, ISO 1000)  1.238 / 1.504 /  2.109 /  3.529  -> 3.2144
foam         (100 fr, ISO 1000)  1.043 / 1.087 /  1.177 /  1.359  -> AboveLadder
```

`foam` on the extended ladder (4/8/16/24/32 -> 1.359/1.727/2.452/3.171/3.903) solves at
**21.9934** exactly, reproducing M52's figure. See error 1 in section 9 for how I nearly
reported this without running it.

## 8. Findings that do NOT appear in the eleven folded rows

**This is the section the orchestrator asked for first among the recoverable material.**
Comparing my report against the eight rows whose substance was quoted to me, the following
appear to be unfolded. Rows 714, 718 and 720 may cover up to three of them; I cannot tell.

| # | Finding | Why it matters |
| --- | --- | --- |
| 1 | **U1 — fact 23's `0.868%` attributed to Tenengrad when it is the ring operator; the shipped value is `0.022%`, 39x lower** | my highest-severity finding; user-visible; wrong today; duplicated in `strehl-core` |
| 2 | **U5 — `--stats` help says 494 MB, the same run prints 527 MB** | user-visible; self-refuting inside one execution |
| 3 | **D1 — `MergeOptions::target_n_eff`'s doc still carries fact 324's superseded ladder** | fact 627 named this sentence two days earlier and the duplicate survived the fix |
| 4 | **D4's drift table and the two-constant triage rule** | row 721 records only line rot; the *8 of 20 rungs* and the ISO fingerprint are the usable part |
| 5 | **D8 — `TenengradSquared` instructs a contributor to do work fact 662 has ruled out, on the wrong crate** | wastes a contributor's time rather than merely misinforming |
| 6 | **D6 — fact 436 cited without facts 631/632's scoping** | |
| 7 | **C1 — fact 627's "ISO-160" parenthetical is wrong; 113 and 112 are ISO 500** | a defect *in section 4*; the correct reading (ISO >= 100) names the mechanism |
| 8 | **The frozen-fixture census result: exactly ONE green-but-false test, six correctly shaped, and the input-vs-claim rule that separates them** | **refutes the brief's expectation that there are more**; the rule is reusable |
| 9 | **The inventory itself: 260 instances / 77 distinct / 18 files vs M49's 58 distinct** | unresolved whether M49 under-counted or the crates grew |
| 10 | **U6 — the `50.9-90.0%` fix is another agent's (`53d06f5`), not mine** | prevents mis-attribution |
| 11 | **Section 7's confirmed-correct denominator** | a defect list without it is not evidence |

## 9. My own errors

Four. The fourth is new, produced by the follow-up audit's correction of row 719, and it
is the worst of them because it is a flaw in the instrument rather than in one reading.

**1. I carried `21.9934` as verified before I had run it.** I conflated M52's extended-
ladder figure with my own shipped-ladder sweep, which returns `AboveLadder` for `foam` and
cannot produce that number. Caught before publishing; re-ran on the extended ladder; it
reproduced exactly. **The number is right and my grounds for it were not, until they were.**

**2. I nearly reported `flat_ratio.rs`'s fact-441 fixture (1.5989) as stale** by comparing
it against the merge's **high-pass** spread (1.5032 on ROI `3056,416`). Fact 441 is a
**raw**-sd statistic. Comparing two different statistics and calling the difference drift
is discipline 264's shape — a discipline I committed myself. Caught before publishing.

**3. I initially recorded the `50.9-90.0%` string as an M56 finding.** It is another
agent's fix in `53d06f5`, landed mid-audit. Caught by reading the log.

**4. NEW — "all four `profile.rs` sites cite `M25 fact 200`" was a substring artifact, and
so was my eight-site fact-439 list.** Both counts came from a grep on a substring
(`M25 fact`) and from a `(fact number, file)` grouping index, and I wrote prose from the
tallies instead of from the quoted lines — **which I had captured and which are printed in
sections 3.5 and 3.8 of this document.** The consequences:

- `profile.rs` `:92` cites `200a`, a different defect from the other three.
- Only **two** of my eight fact-439 sites quote the span; five quote a `k` that fact 635
  leaves untouched; and **three sites quoting `6.680` were missing from the list entirely
  — the same index over-counted and under-counted at once.**

**5. NEW — I named `DEFAULT_SPECKLE_TOLERANCE` as U1's second site from memory, and it is
in none of my captured evidence.** Correcting it from `join_a.txt` and `raw_fact_lines.txt`
showed the finding was wrong in a second way as well: **fact 23's row names no operator**,
so the defect is an *invented attribution*, not a misquotation — and **two sibling sites
quote the row correctly and must not be edited**, which I had not noticed because I had
grouped by fact number again. Full correction in section 4.1. This error was caught only
because the orchestrator asked a routing question precise enough that memory was not good
enough to answer it, which is itself the finding: **"which symbol, which crate" is a
question that forces you back to the evidence, and "is this citation wrong" is not.**

**The general lesson, and I think the most valuable thing in this report:** I built an
instrument that indexes citations *by number*, then used it to make claims about what the
citations *say*. That is M49's error committed by the agent hired to correct M49's error,
one level up. **An index keyed on the number cannot answer a question about the content**,
and the fix is not a better index but a rule: **every claim about a citation must quote the
citation.** Both defective claims would have died on contact with their own captured
evidence.

## 10. What I did not check

- **~68 of the 260 instances were content-checked but not re-measured.** Where a citation
  was a correct *characterisation* with no number attached, I read the row and stopped.
  Any stale number in that set is undetected.
- **Fact 500's 1.815 was not re-measured** — the plugin survey has no radius-2 arm and I
  did not add one, being read-only in `crates/`.
- **M8's memory constants were not re-measured.** Python here has no `psutil`. U5's 494 vs
  527 MB was caught from the binary's own printed report, not from RSS.
- **Fact 635's "single consistent convention" was not tested.** I measured the operators'
  `k` under the shipped window and got a 10.27x span; I did not re-run them under a
  unified convention to check the 2.12x claim.
- **No clippy run.** Lints were out of scope and may carry their own citations.
- **Five of seven citations that appeared mid-audit are unchecked.** The tree moved six
  times while I worked; I pinned to `d7eedfa` and did not re-enumerate.
- **I did not determine whether M49 under-counted or the crates gained 19 numbers.**
- **The binary was built at `90e7db5`, not `d7eedfa`.** I checked the intervening commits
  for changes to measured paths and found only `53d06f5` (U6), but I did not rebuild.

## 11. Proposed entries, numbered locally from 1

Numbered locally per house style. Several of these have already been folded from the lost
report; they are restated so the fold has a committed source.

### Facts

1. A citation audit that checks *number validity* and one that checks *content support*
   are different instruments. M49 found 100% of cited numbers resolved; on the same corpus
   this audit found content defects at 5 user-visible sites. **MEASURED.**
2. `merge_cmd.rs`'s speckle companion attributes fact 23's `0.868%` regularised figure to
   Tenengrad; it is the ring difference. The shipped regularised-Tenengrad value is
   `0.022%`, 39x lower, and is printed one line earlier in the same output. **MEASURED.**
3. `--stats` help states 494 MB per worker; the same binary in the same run reports 527
   MB/worker. **MEASURED.**
4. Of seven tests asserting against frozen measured data, exactly one is green-but-false.
   A fixture is safe as a function's *input* and unsafe as a stand-in for the *pipeline
   output* the test's name claims to characterise. **MEASURED.**
5. The `LADDERS` fixture is stale on 8 of 20 rungs, and the staleness is confined to the
   two ISO-50 stacks — the fingerprint of `2a4f5c5`'s `max(iso, 100)` floor. **MEASURED.**
6. A measurement predating `2a4f5c5` is suspect iff it involves ISO < 100; one predating
   `f95f6f4` is suspect iff it involves ISO >= 400. **DERIVED.**
7. Fact 627's parenthetical "the ISO-160 ones" is wrong: two of the three are ISO 500. The
   shared property is ISO >= 100. **MEASURED.**
8. A citation index keyed on the fact *number* cannot support a claim about what the
   citing sites *say*; this audit made that error twice, in the directions of both
   over- and under-counting, from a single grouping. **MEASURED, on my own output.**

### Disciplines

1. **Every claim about a citation must quote the citation.** Counts from a grep or a
   grouping index are a search result, not a finding.
2. **Cite code by symbol name or quoted content, never by line number.** Fact 581's
   `:25,:40,:45` rotted to `:72,:87,:92,:112` in one milestone.
3. **When a caveat is applied to one row, check its sibling.** `merge_cmd.rs` states the
   operator caveat correctly for fact 19 and incorrectly for fact 23, ~210 lines apart.
4. **Fixing the user-visible copy of a wrong number does not fix the duplicate.** Fact 627
   fixed the CLI help; the identical sentence in `MergeOptions::target_n_eff`'s doc
   survived.
5. **A park ("pending M<NN>") must name the condition that lifts it**, or it becomes a
   decision when the milestone lands.
6. **An agent that returns a report must also commit it.** Rule 31 is unenforceable
   against text that exists only in a context window. This document is the proof.

### Questions

1. Did M49 under-enumerate at 58 distinct numbers, or did `crates/` gain 19 in the
   interval? The answer decides whether citation density is outrunning checking.
2. Should section 4 publish a regularised-Tenengrad speckle, given the shipped pipeline
   produces one (`0.022%` / `0.025%`) and code invented a reference point for its absence?
3. Should provenance cells carry the source commit sha, making an uncommitted fold
   impossible to complete rather than merely against the rules?
4. Does fact 635's 2.12x span reproduce under a unified window convention? Not measured
   here.
5. What is the correct disposition of `TenengradSquared` now that fact 662 has invalidated
   change (c) as specified?
