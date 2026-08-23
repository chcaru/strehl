# M58 — the citation-content defects, verified against the rows and repaired

**Milestone M58.** Commissioned to act on M56's citation-*content* audit (facts
713-723) across `crates/strehl-plugin/**`, `crates/strehl-core/src/through_focus.rs`
and `crates/strehl-cli/src/stack.rs`. The brief was explicit that M56's evidence
was being handed over, **not** M56's conclusions, and that finding M56 wrong
would be worth more than a fix.

Labels are per rule 8: **MEASURED** (I ran it and read the output), **DERIVED**
(exact arithmetic on measured or published quantities), **ARGUED** (reasoning
from structure, no new number), **CORPUS** (a number I am quoting from
`SYNTHESIS.md` without re-measuring it — flagged as such wherever it appears).

---

## 0. Pre-registration

Written before the deciding runs. Rule 20: each criterion names an input that
would make it fail.

### P1 — the fact-500 decomposition

`through_focus.rs:124` and `:514` quote `k = 5.94`. Fact 500 says that ratio
"mixes a window-radius change with the presence of a 17x17 box" and that the
honest same-configuration quantity is **1.815**. The brief notes fact 500's
1.815 was *not* re-measured by M56 and must be treated as a corpus number.

`strehl-plugin` can measure it, because `FieldConfig` carries the regulariser as
an explicit `Option<usize>` and `Tenengrad::at_radius` carries the window. I will
calibrate three configurations at `CalibrationPlan::host_default()`
(512² × 12 seeds, the plan the host would actually pay for):

| arm | operator | regulariser | what it is |
| --- | --- | --- | --- |
| **A** | tenengrad w13 | r8 | the **selection** field as consumed → should reproduce `FOCUS_NOISE_SD` |
| **B** | tenengrad w2 | none | the **fine** field as consumed → should reproduce `FINE_FOCUS_NOISE_SD` |
| **C** | tenengrad w2 | r8 | fact 500's same-configuration quantity, `SD(regularise(box_mean(\|grad\|,2)))` |

**Criterion P1.** I accept fact 500 iff **all three** hold:

- `C/A` ∈ **[1.76, 1.87]** (±3% of 1.815) — the honest window-only ratio;
- `B/C` ∈ **[3.18, 3.37]** (±3% of 3.273) — the regulariser term;
- `B/A` ∈ **[5.76, 6.12]** (±3% of 5.942) — the as-consumed ratio.

If `C/A` misses, fact 500's *replacement* number is wrong, and substituting it
into `through_focus.rs` would be the project shipping a second wrong constant to
replace the first — the exact failure fact 580 parked the change to avoid.
If `B/A` misses, one of the two published constants does not reproduce on the
plugin's pipeline, which is a larger finding than anything in the brief.

### P2 — which of the three prose sites is actually refuted

Fact 580 names three prose sites as "asserting the refuted `k = 5.94`":
`through_focus.rs:124`, `through_focus.rs:514`, `strehl-plugin/src/lib.rs:18`.
I predict, **before measuring**, that they are not the same defect:

- `lib.rs:18` uses 5.94 as *a plugin operator's* `k`. A plugin is always
  calibrated through the host's regulariser, so its `k` is arm C over arm A.
  No operator reachable by that path has `k = 5.94` from this pair. **Refuted.**
- `through_focus.rs:124` says the constant "is 5.94x larger than
  `FOCUS_NOISE_SD`". That is arithmetic on two published constants and is
  **true**; what fails is the following clause, "and that is the whole trade",
  which attributes the whole factor to the window.
- `through_focus.rs:514` says a disagreement rate is "what a 5.94x noisier field
  should do". Both fields there are consumed in DN-normalised units — the fine
  one unregularised by design, the selection one regularised — so the ratio the
  sentence needs is exactly `B/A`.

**Criterion P2.** If `B/A` lands in P1's band, then `through_focus.rs:514`'s
number is **correct for its sentence**, fact 580 over-names it, and substituting
1.815 there would *introduce* an error. In that case I will not substitute, and I
will say fact 580 is wrong on that site. If `B/A` misses the band, P2 is
withdrawn and I substitute wherever fact 580 says.

### P3 — the gate/pixel-fraction pairing

`reference.rs:259-261` pairs SML's `k = 6.680` (→ effective gate 0.150) with
**87.76%**, which is M43's row for gate **0.168**.

**Criterion P3.** Run `strehl merge` on `109MSDCF` at gates 0.150 and 0.168 and
read `n_eff=1 %`. The pairing is confirmed wrong iff the 0.168 row reproduces
M43's 87.76% to four figures **and** the 0.150 row differs from it by more than
the CLI's own reporting resolution (0.01 pp). If the two rows agree to within
that, the "defect" is cosmetic, no user-visible number is wrong, and I say so
instead of editing.

### P4 — the cost bound

Fact 505's `~1.7 ms per stage` is quoted at five sites, and fact 505's own
Source column forbids quoting it.

**Criterion P4.** Run the crate's own probe in release. The prohibition is
confirmed necessary iff the measured per-plane cost exceeds **2×** the 1.7 ms
bound. If it comes in at or below 1.7 ms, then fact 525 and M56 are both wrong,
the bound stands, and the five sites need no change — which I would report as the
finding.

### P5 — the citation count for fact 439's span

Fact 723 states fact 439's "spans 10.4x" is "quoted at eight sites". The brief
enumerates them: `lib.rs:16` plus `reference.rs` at `:1, :16, :25, :213, :259,
:308, :420`.

**Criterion P5.** I will read all eight and classify each as *quoting the span*
or *citing fact 439 for something else*. If fewer than eight quote the span, the
count is an over-count and I report it, because it is the same shape of error
M56 charged M49 with in fact 713 — a survey counting a different thing from what
its row implies.

### Negative controls

Every code change that carries a number gets a test that recomputes the number,
and every such test gets a deliberate regression that must turn it red. Restores
are done from a copy in `$env:TEMP` with `LastWriteTime` reset, never with
`git checkout --` (rule 33 and the M54 brief: five agents are writing to this
tree).

---

## 1. Headline

**Every one of M56's five defect groups is a real defect in the text, and in
three of them M56's own account of the defect is itself wrong** — it over-counts
the fact-439 sites by 4x, misses three sites that need the same scoping, and
names a `through_focus.rs` site whose number is *correct* and would have been
made wrong by the prescribed substitution. Fixed all five; refuted three pieces
of the framing; and the one number the brief told me to take on trust (fact
500's 1.815) turns out to have been measured twice already and is now measured
three times, in two languages and two crates, with a spread of 0.21%.

---

## 2. Findings

Numbered for folding. Every number carries MEASURED / DERIVED / ARGUED.

### F1 (MEASURED) — fact 500's decomposition reproduces, in Rust, in two crates

The plugin calibrator (`host_default`: 512^2, 12 seeds, SplitMix64 -> Box-Muller):

```
A  selection  w13 + r8   1.5211264e-2 +/- 7.566e-5     (FOCUS_NOISE_SD      0.015214)
B  fine       w2  bare   9.0399854e-2 +/- 1.697e-4     (FINE_FOCUS_NOISE_SD 0.090400)
C  fine       w2  + r8   2.7553098e-2 +/- 8.997e-5     (fact 500's 0.027613, -0.21%)

window term        C/A = 1.8114     fact 500: 1.815
regulariser term   B/C = 3.2809     fact 500: 3.273
as consumed        B/A = 5.9430     the published constant pair: 5.942
```

`strehl-core`'s independent path (`compute_with_fine` + `merge::regularise`,
same 12 seeds, margin 23 so all three arms share one interior) gives
**5.9463 / 1.8109 / 3.2835**. Two code paths that share no calibration code
agree to 0.1%.

**Fact 500's 1.815 is not a corpus number.** The brief said M56 had not
re-measured it and I should treat it as corpus. True of M56 — but
`M52-gate-cluster-verified.md:99-100` already records 0.027605 against M43's
0.027613 (+0.03%, `k = 1.8145`). Mine is the **third** independent measurement
and the first in Rust. It should be promoted from a single-source number.

**Rule 34 disclosure.** These plants share `FOCUS_NOISE_SD`,
`FINE_FOCUS_NOISE_SD`, `WINDOW_RADIUS`, `FINE_WINDOW_RADIUS` and
`REGULARISER_RADIUS` with the code under test, and the unit-sigma noise model
makes the normalisation divisor exactly 1.0. So they can prove **nothing** about
the absolute calibration; they test the operator chain and the two window radii,
which is all they claim. The absolute constants are falsifiable only against real
sensor data.

### F2 (DERIVED from F1) — fact 580 over-names `through_focus.rs:514`; the prescribed fix would have introduced an error

Fact 580 lists five sites quoting `k = 5.94` and fact 500 calls that ratio a
3.27x overstatement. Because `B/A = 5.9430` is a real, reproducible quantity,
the three prose sites are **three different situations**, not one:

| site | what 5.94 was doing | verdict |
|---|---|---|
| `strehl-plugin/src/lib.rs:18` | used as *a plugin operator's* `k` | **genuinely refuted.** A plugin is always calibrated through the host regulariser, so its `k` is `C/A = 1.81`. Replaced the illustration with SML. |
| `through_focus.rs:124` | "5.94x larger than `FOCUS_NOISE_SD`" | **arithmetically true.** The failing clause was the trailing "and that is the whole trade". Fixed by *decomposing*, not substituting. |
| `through_focus.rs:514` | "what a 5.94x noisier field should do" | **the number is correct.** Both fields enter that comparison exactly as the merge consumes them — selection regularised, fine raw — so the ratio the sentence needs *is* `B/A`. Substituting 1.815 would have understated the predicted disagreement rate by 3.27x. |

I fixed `:514` by keeping 5.94 and adding the clause that distinguishes "the
as-consumed ratio" from "an operator `k`". **This is a correction to fact 580,
not to the code.**

### F3 (MEASURED) — the gate/pixel-fraction pairing in `reference.rs` is wrong, and M56's replacement number is right

`strehl merge D:\personal\macro\109MSDCF --gate 0.150 0.168 1.0`, 22 frames:

| declared gate | tolerance | mean `n_eff` | **`n_eff = 1`** |
|---|---|---|---|
| 0.150 | 0.003227 | 1.117 | **89.02%** |
| 0.168 | 0.003615 | 1.131 | **87.76%** |
| 1.000 | 0.021516 | 1.884 | 41.66% |

Reproduces M43's cost table to four figures at 0.168 and confirms M56's 89.02%
at 0.150. `reference.rs:259-261` paired fact 439's `k = 6.680` gate (0.150) with
M43's fraction for `k = 5.94` (gate 0.168). Corrected to **89.02%**.

**M52 found this first, one layer up.** `M52-gate-cluster-verified.md:464-466`
records the same mis-pairing in `docs/proposals/E-plugin-architecture.md` §F4.6
fault 5. `reference.rs` evidently inherited the error from the design doc, and
**the design doc still has it** — see the hand-off in §5.

### F4 (MEASURED) — the cost bound is refuted, and the example printed the refuted figure to the user

`cargo run --release --example f5-design-probes`, probe 3:

| operator | per registration | per plane | vs the 1.7 ms bound |
|---|---|---|---|
| tenengrad | 59.73 ms | 4.98 ms | **2.93x** |
| sml | 63.01 ms | 5.25 ms | 3.09x |

Agrees with M56's 4.99 / 59.84 to 0.2% and with fact 525's 5.02 / 60.3 to ~1%.
The `println!` at `examples/f5-design-probes.rs:141` printed the refuted 1.7 ms
bound and then measured against it in the same breath, so a contributor read a
2.9x violation as a defect. Rewritten to name the bound REFUTED, point at
fact 525's 5.02 / 60.3, and say that *beating* 1.7 ms would mean the probe had
stopped measuring.

### F5 (MEASURED + DERIVED) — fact 723 over-counts the fact-439 sites by 4x and misses three others

I read all eight sites the brief names. They are not eight instances of one claim:

| class | sites | does fact 635's scoping bite? |
|---|---|---|
| literal `"spans 10.4x"` | `lib.rs:16`, `reference.rs:16` | **yes** |
| a span *endpoint* (ring 0.644) | `reference.rs:25`, `:308` | **no** — ring folds no constant, so 635 leaves it unchanged |
| an individual convention-dependent `k` | `reference.rs:213` (6.590), `:259` (6.680) | **yes** |
| bare citation, no number | `reference.rs:1`, `:420` | n/a |

So the literal claim is over-counted **4x** — the same shape of error M56 charged
M49 with in fact 713. **And M56 under-counted:** `calibrate.rs:908`, `:922` and
`registry.rs:386` all quote fact 439's 6.680 and were not named. The set that
genuinely needs a scoping is
`{lib.rs:16, reference.rs:16, :213, :259, calibrate.rs:908, :922, registry.rs:386}`.
All seven now carry it.

Re-measured the survey in-crate (512^2, 12 seeds): ring 0.6437, tenengrad 0.9998,
tenengrad-sq 1.3592, brenner 1.9694, local-variance 2.4806, laplacian 6.5235,
**sml 6.6118** -> **span 10.272x**, SML effective gate **0.1512**. Confirms
M56's 10.27; the number reproduces and it is only the *scoping* that was missing.

**Fact 635's mechanism, measured:** SML `k` = 6.6118; the same operator with 1/8
folded into the stencil = 0.8265; ratio **exactly 0.125000**. The pipeline
(respond -> box_mean -> /sigma -> box_mean) is linear in the response, so a
scalar fold scales the SD exactly. Fact 635's arithmetic prediction is
6.680/8 = 0.835 (-1.0% against my 0.8265).

Fact 635's **2.12x** I did *not* re-measure and have labelled CORPUS wherever it
now appears. Reason: under "every operator otherwise unchanged" only the
Laplacian family (/8), Brenner (/2) and local variance (SD-not-variance) move,
and 1.367/0.644 = **2.1226** falls out arithmetically for the first two — but
local-variance-as-SD is *not* derivable that way, because sqrt is not linear.
Naming the gap rather than inventing the number.

### F6 (MEASURED) — fact 717's implication is false: the citable form already exists

Fact 717 says *"A report-local number that folded as a QUESTION has no citable
form, and nobody defined one."* There are **four counter-examples in `crates/`**:
`merge_cmd.rs:21` ("question 90"), `merge_cmd.rs:681`, `focus.rs:78` ("SYNTHESIS
open question 17"), `profile.rs:353` ("SYNTHESIS question 129"). The
`strehl-cli/src/stack.rs` fix was therefore a one-word substitution, not a design
gap.

### F7 (MEASURED) — one third of defect 5 was already fixed, 12 minutes before I looked

The brief names `stack.rs:358`, `stack.rs:385-386` and `profile.rs:92`.
`profile.rs` was fixed at HEAD by commit **`cc2af9f`** ("profile.rs: cite the
folded fact numbers, not M25's report-local ones", 13:10 today), in the *better*
form — it keeps M25's provenance and resolves it: *"(M25 fact 200a, which folded
as SYNTHESIS *question* 126 — it is an open question, not a fact)"*. Not a defect
to route. This is concurrency, not an M56 error: the audit ran before 13:10.

I deliberately did **not** copy that longer form into the printed string. A doc
comment is read by someone holding the repository; `provenance_line` is printed
to a *user*, who cannot reach `M25-simulator-measured.md` at all and can only
follow a SYNTHESIS number. The printed line now reads:

```
                  is measured, but the ISO at which it starts is not (SYNTHESIS question 126
                  -- the corpus holds no ISO 64 or 80 capture).
```

### F8 (MEASURED) — the test that guarded the 5.94 ratio had no power at all

`through_focus.rs`'s `the_fine_scale_is_much_noisier_than_the_selection_scale`
read `assert!((5.0..7.0).contains(&(FINE_FOCUS_NOISE_SD / FOCUS_NOISE_SD)))`.
Both terms are compile-time constants *of the crate under test*: rule 35 exactly.
M52 flagged it as "the framing fact 500 retired"; by F2 the framing is defensible
and the **power** was the defect.

Negative control NC2 proves this concretely rather than by assertion. Regularising
the fine arm — a real defect, and the single most likely way this code could go
wrong — moves the observable from 5.9463 to 1.8109 and the regulariser term from
3.2835 to exactly 1.0000. The old test touches neither constant, so it is green
under that regression **by construction** (DERIVED, trivially). The rewritten
test fails, and localises to the fine arm.

### F9 (MEASURED) — a gap in rule 33 as written

Rule 33 says a `cargo test` result with no `Compiling` line above it is not
evidence. **`cargo clippy` never prints `Compiling`** — it prints `Checking`. I
filtered for `Compiling` and read three consecutive clean clippy runs as
"suspiciously cached", then burned a probe cycle injecting a deliberate lint to
prove the toolchain was live. It was: the *filter* was wrong, not cargo. Rule 33
should name both verbs.

---

## 3. Pre-registered criteria: results

| # | criterion, registered in §0 before the deciding run | result |
|---|---|---|
| P1 | The three fact-500 ratios land in [1.76,1.87], [3.18,3.37], [5.76,6.12] | **MET** — 1.8114 / 3.2809 / 5.9430 |
| P2 | If P1 holds, at least one of the three prose `k = 5.94` sites is *correct as written* | **MET** — two of three (F2) |
| P3 | `n_eff = 1` fraction differs between gate 0.150 and 0.168 by > 0.01 pp | **MET** — 1.26 pp (89.02 vs 87.76) |
| P4 | Measured per-plane cost exceeds the 1.7 ms bound by > 2x | **MET** — 2.93x |
| P5 | The eight named fact-439 sites are *not* eight instances of one claim | **MET** — 2 literal, 2 endpoint, 2 individual-`k`, 2 bare (F5) |
| C4 | The `stack`/`merge` provenance line emits no `fact <digits><letter>` token | **MET** — verified by running the binary, and pinned by a test |

---

## 4. Negative controls

Every new or rewritten test was deliberately regressed and confirmed red. All
restores were from a `$env:TEMP` copy with `LastWriteTime` reset; **no
`git checkout --` was used at any point.**

| # | test | regression injected | result | traces left after restore |
|---|---|---|---|---|
| NC1 | `every_citation_the_binary_prints_resolves_to_synthesis_or_the_source` | reinstated `"(fact 200a -- ...)"` in the printed string | **RED** at `stack.rs:1080` | 0 |
| NC2 | `the_fine_scale_is_much_noisier_than_the_selection_scale` | regularised the fine arm | **RED** at `through_focus.rs:1224`, ratios 1.8109 / 1.0000 | 0 |
| NC3 | `the_fine_constant_factors_into_a_window_term_and_a_regulariser_term` | arm B `FieldConfig::BARE` -> `SHIPPED` | **RED**, regulariser term 1.0000 | 0 |
| NC4 | `rescaling_a_stencil_moves_its_k_by_exactly_that_scale` | `*o *= self.scale` -> `self.scale.sqrt()` | **RED**, ratio 0.353553 | 0 |

**NC3's restore silently failed on the first attempt** (a PowerShell block exited
1 with no output and the `Copy-Item` never ran), and the file sat regressed until
I checked line 660 by hand. The protocol caught it because verifying the restore
is a separate step from performing it. It would not have been caught by trusting
the exit code — the exit code was for a *later* statement in the same block.
Recommend the fold record this: **verify a restore by reading the restored line,
never by reading an exit code.**

---

## 5. What I changed

| file | change |
|---|---|
| `strehl-plugin/src/lib.rs` | fact 436 block rewritten with fact 631's scoping (`t/k` is a price, not a repair); fact 439 block rewritten with fact 635's; the `k = 5.94` illustration replaced with SML `k = 6.68` -> gate 0.150 -> **89.02%** vs 41.66%, plus a paragraph on why 5.94 was retired here; fact 509 block rewritten per fact 662; `:58` cost bound marked refuted with fact 525's 5.02/60.3 and my 4.98/59.73 |
| `strehl-plugin/src/reference.rs` | module doc `:16` (10.4x scoped, 10.27x measured) and `:18-20` (87.76% -> **89.02%**); `TenengradSquared` doc retargeted fact 509 -> fact 662 with the change marked blocked; `Laplacian` `:213` marked convention-dependent; `SumModifiedLaplacian` `:255-264` gate/fraction corrected; `Ring` noted as surviving the convention change; **new test-only `Rescaled` wrapper + `rescaling_a_stencil_moves_its_k_by_exactly_that_scale`** |
| `strehl-plugin/src/registry.rs` | module doc scoped by fact 631; `:378` test doc scopes 6.680 as this repo's SML |
| `strehl-plugin/src/calibrate.rs` | `# Cost` and `host_default` docs now cite fact 525's measured figures and record 505's bound as refuted; `:880` test doc scopes 6.680/1.367 by fact 635; **new test `the_fine_constant_factors_into_a_window_term_and_a_regulariser_term`** |
| `strehl-plugin/src/measure.rs` | `:83` `Window::Custom` doc bounded by fact 525's 5.02 ms |
| `strehl-plugin/examples/f5-design-probes.rs` | the **user-visible `println!`** at `:141` rewritten (F4) |
| `strehl-core/src/through_focus.rs` | `FINE_FOCUS_NOISE_SD` doc carries the measured decomposition `5.943 = 1.811 x 3.281` with a diagram and an explicit "never quote 5.94 as an operator `k`"; `:514` keeps 5.94 and gains the clause that distinguishes as-consumed from operator `k`; **`the_fine_scale_is_much_noisier_than_the_selection_scale` rewritten from a constant-ratio assertion into a three-arm measurement** (F8) |
| `strehl-cli/src/stack.rs` | `provenance_line` printed string `:385-386` "fact 200a" -> "SYNTHESIS question 126"; the `:358` comment likewise, with the reasoning for the shorter form; **new test `every_citation_the_binary_prints_resolves_to_synthesis_or_the_source`** |

### Hand-offs — files I do not own

1. **`docs/proposals/E-plugin-architecture.md` §F4.6 fault 5** carries the same
   `k = 6.68` / 87.76% mis-pairing that `reference.rs` inherited (F3). M52
   reported it at `M52-gate-cluster-verified.md:464-466` and it is still there.
   Correct value at gate 0.150 is **89.02%** (MEASURED, §F3). Not in my
   assignment and not a `crates/` file.
2. **Fact 580's site list** should drop `through_focus.rs:514` and should not be
   used to drive a mechanical substitution at `:124` either (F2). No code change
   needed — this is a correction to the fact row.
3. **`crates/strehl-cli/src/merge_cmd.rs`** — its two `k = 5.94` sites were
   already corrected in another agent's work while I was running (`:1579`,
   `:1583`, `:1587`, `:1660` now cite 1.815 and M52's 1.8145). Nothing to route.
4. **`profile.rs:92`** — already fixed at `cc2af9f` (F7). Nothing to route.

### What I did not do, and why

- **Did not invent fact 635's 2.12x in a new configuration.** Local variance as
  an SD is not derivable from the scalar-fold argument (F5). Labelled CORPUS
  everywhere it appears; the gap is named in the doc text itself.
- **Did not re-measure fact 500's 1.815 against real sensor data.** Both my
  plants share the normalisation constant with the code under test (F1's rule 34
  disclosure), so neither can speak to absolute calibration.
- **Did not touch `FOCUS_NOISE_SD` or `FINE_FOCUS_NOISE_SD`.** F1 measures them
  at 1.5211e-2 and 9.0400e-2, agreeing with the shipped constants; and M48's
  re-derivation of `FOCUS_NOISE_SD` under the new read-noise constant is a
  separate live milestone.

---

## 6. Verification

All runs read directly, none with `-q`.

```
cargo fmt --all -- --check                       exit 0
cargo clippy --workspace --all-targets           exit 0, no warnings
                                                 ("Checking strehl-plugin" line read -- see F9)
cargo test --workspace
    Compiling strehl-core / strehl-raw / strehl-plugin / strehl-cli   [all four read]
    strehl-cli     40 passed
    strehl-core   126 passed
    strehl-plugin  35 passed
    strehl-raw      8 passed
    doc/integration 1 passed
    ---------------------------------
    210 passed, 0 failed
```

Baseline at briefing was 187. The workspace has since grown from other
milestones' work; my own contribution is **+3 tests** (plugin 33 -> 35, cli
39 -> 40) and **one rewrite** (`strehl-core`, no count change).

Binary behaviour confirmed by running it, not by reading the source:
`strehl stack D:\personal\macro\109MSDCF` — the provenance block now emits
`(SYNTHESIS question 126 -- the corpus holds no ISO 64 or 80 capture)`.
`strehl merge D:\personal\macro\109MSDCF --gate 0.150 0.168 1.0` produced §F3's
table. No path under `D:\personal\macro\` was written to.

---

## 7. Summary for the fold

- **Three corpus corrections:** fact 580 over-names `through_focus.rs:514` (F2);
  fact 723 over-counts by 4x and under-counts by three sites (F5); fact 717's
  "nobody defined one" is false, with four counter-examples (F6).
- **One promotion:** fact 500's 1.815 now has three independent measurements
  (M43 0.027613, M52 0.027605, M58 0.0275531 — spread 0.21%), the last two in
  Rust. It should no longer read as single-source (F1).
- **One rule amendment:** rule 33 should name `Checking` alongside `Compiling`,
  because `cargo clippy` only ever prints the former (F9).
- **One process note:** verify a restore by reading the restored line, not by
  reading an exit code (§4, NC3).
- **One hand-off outside `crates/`:** `E-plugin-architecture.md` §F4.6 fault 5
  still pairs `k = 6.68` with 87.76%; the measured value is 89.02% (F3).
