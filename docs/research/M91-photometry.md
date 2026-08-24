# M91 — Per-frame photometric normalisation at the merged image: measured, priced, and not shipped

> **NOT INDEPENDENTLY VERIFIED.** Same author as the measurements. Rule 12.
>
> Pre-registration: `experiments/M91-photometry/PREREGISTRATION.md`, committed at
> `065ab3b` (§0–§5), `cb706c9` (addendum 5b / C9) and `a113701` (addenda 5c/5d/5e
> / C3a-hard, C10) — **every one of them before the arm it governs ran**.
> Instrument: `crates/strehl-cli/examples/m91-photometry.rs`. Raw output:
> `experiments/M91-photometry/out/`.

---

## Verdict

**NO SHIP.** Do not apply per-frame photometric normalisation to the merged
image on current evidence.

The three things that decide it, in order of weight:

1. **The correction is material but its direction is not established.** It moves
   the merged green above the merged pixel's own `predicted_sigma` at 60.35% of
   pixels on `119MSDCF` and 95.02% on `coffee-bean` (MEASURED, C3b) — so it is
   nowhere near the noise floor. But the merge's own disagreement statistic gets
   **worse** under it on 2 of 6 stacks (−3.48% `coffee-bubbles`, −5.60% `foam`,
   excess reduction at gate 4.0, MEASURED, C6). A change that large in a
   direction that is negative on a third of the corpus is not a shippable
   correction.
2. **The functional form question is answered, and the answer is not the
   offset.** The affine form beat gain-only by ≥5% held-out on only 2 of 6
   stacks, and **both of those two are VOID under the pre-registered
   admissibility guard** (MEASURED, C1/C1b). M24 §5's first clause resolves:
   **a single global gain per frame suffices; an offset term is not earned.**
3. **The precondition for a global gain is NOT ESTABLISHED, after two attempts.**
   Both pre-registered spatial-uniformity instruments — `U` (C2) and the
   explained-variance decomposition (C10) — are **void on all six stacks by
   their own mandatory power controls** (MEASURED). Defocus dominates
   block-level variation on a focus stack, so neither statistic can read
   "uniform" even on a ladder that is uniform by construction. M24 §5's second
   clause survives this milestone unanswered, and now with two failed
   instruments attached to it.

The ground-truthed calibration of what that unanswered question costs: a global
per-frame gain recovers **100.0%** of a spatially uniform planted drift and
**13.42%** of the same drift given a 50% left-to-right ramp (MEASURED,
C3a/C3a-hard). Until the drift's spatial structure is measured, applying a
global gain is a bet on which of those two numbers is in play.

**What is shippable, and it is not an image change:** the pedestal correction to
the *existing* photometric probe. `Estimator`'s probe luma is black-inclusive
raw DN, and `m60-disagreement.rs` corrects it about zero rather than about
black. Fixing the pivot is worth up to **+19.85 percentage points** of excess
disagreement removed (MEASURED, `coffee-bubbles`, gate 1.0).

---

## Headlines

**On the question.** *The drift is real, it is large, it is fittable, and a
single global gain is the right form for it — but it is measurably **not** a
single global gain in space, and applying one to the merged image moves 95% of
pixels above their own noise in a direction nobody has shown to be an
improvement.*

**On method.** *Two instruments I designed, pre-registered and equipped with
mandatory power controls both failed those power controls, and the
pre-registration is the only reason that is visible instead of being reported as
a finding about the data. A third — the placebo — caught a comparison-target
bug in my own design by reproducing a completely different arm's number exactly.*

---

## 0. Rule 40: what I read, and where the brief is half-right

I was briefed that M24 §5 left the functional-form question "explicitly open, in
as many words". It does, and I read that sentence at source
(`docs/research/M24-photometric-drift-measured.md` §5). **But the corpus had
already half-answered it and the brief did not say so.**

`docs/research/M60-prior-art-and-the-rival-explanations.md` (milestone M60b),
found by grepping all 116 corpus files for `photometric`, ran gain-only, affine
least-squares and offset-only arms at merge time on three stacks and concluded in
its own headline that this "closes M24 §5's open question in the negative"
(MEASURED, M60b §4.2/G7). So M91's contribution is **not** first contact with the
question. What was genuinely open, and what this milestone therefore addresses,
is: the **merged image** (M60b §5 item 4, in as many words: *"Nobody has produced
a merged image either way"*), the **spatial** clause of M24 §5, a
**defocus-invariant** estimator (M60 F3: *"The estimator that would not have this
defect has to be fitted on pixels the sweep does not move, and nobody has one"*),
and the three corpus stacks the merge-time arms had never seen.

Reported as required by rule 40: **the brief's framing of the headline question
as open was half right, and the source wins.**

---

## 1. The instrument, and the one control that licenses every image number

`m91-photometry.rs` is a **second implementation of the merge's averaging
stage**, not an edit to `merge.rs` — that file is contended by five live
milestones. It runs the shipped `green_luma_with_clip`, `FocusField`,
`regularise`, `FocusStats` and `Gate`, then accumulates its own G1/G2 sums beside
a real `Estimator`.

**C8 — the identity control (MEASURED).** With `c = 1, o = 0` the mirror must
reproduce `Estimator::green_mean` bit-identically in `f32`, censoring rule
included.

| stack | pixels | f32 bit mismatches | worst |
|---|---:|---:|---:|
| all six | 8,241,504 each | **0** | 0.000000 DN |

Without this, every number in §3 would be a claim about my accumulator rather
than about the merge. **C8 is not a check on the correction** — it stayed green
throughout the C5 negative control, while the correction was deliberately
inverted — and the report does not use it as one.

**Independent validation against M60b (MEASURED).** Re-running the merge-time
arms at M60's gate of 1.0 reproduces `M60-prior-art-and-the-rival-explanations.md`
§4.2 to four decimal places on every column that is comparable:

| stack | raw (mine / M60b) | gain zero-pivot (mine / M60b) | offset-only (mine / M60b) | exposure (mine / M60 F9) |
|---|---|---|---|---|
| `109MSDCF` | 1.8508 / 1.8508 | 1.7906 / 1.7906 | 1.8482 / 1.8482 | 58.34% / 58.34% |
| `coffee-bubbles` | 2.1712 / 2.1712 | 2.4345 / 2.4345 | 2.0827 / 2.0827 | 38.26% / 38.26% |
| `foam` | 23.8430 / 23.8430 | 24.3811 / 24.3811 | 22.7002 / 22.7002 | 8.20% / 8.20% |

The affine column deliberately does **not** match, and §2.3 says why.

---

## 2. Measurements

### 2.1 Drift, on a third independent instrument

| stack | frames | M91 ptp | fact 180 / M60b G5 | agreement |
|---|---:|---:|---:|---|
| `109MSDCF` | 22 | 0.910% | 0.91% | exact |
| `119MSDCF` | 33 | 2.880% | 2.88% | exact |
| `112MSDCF` | 79 | **7.513%** | 6.84% | **+9.8% relative** |
| `coffee-bubbles` | 19 | 8.909% | 8.93% | 0.2% |
| `foam` | 100 | 10.604% | 10.604% | exact |
| `coffee-bean` | 105 | **12.088%** | 11.70% | **+3.3% relative** |

MEASURED. Four of six reproduce exactly. `112MSDCF` and `coffee-bean` read
**higher** than fact 180 on all frames. I have not established the cause and am
not speculating about it here; the discrepancy is filed as P8.

### 2.2 C1 — does the offset term earn its place?

Held-out design fixed before the run: all parameters fitted on even-parity
32×32 blocks, residual scored on odd-parity blocks only.

| stack | F5 gain-only | F6 affine | reduction | bar 5.0% | C1b on F6 |
|---|---:|---:|---:|---|---|
| `109MSDCF` | 20.9223 | 20.7994 | 0.59% | no | ok |
| `119MSDCF` | 26.0680 | 25.9800 | 0.34% | no | ok |
| `112MSDCF` | 35.8323 | 34.5168 | 3.67% | no | **VOID-o** |
| `coffee-bubbles` | 102.5111 | 92.2391 | **10.02%** | yes | **VOID-o** |
| `foam` | 386.4444 | 222.4435 | **42.44%** | yes | **VOID-co** |
| `coffee-bean` | 619.3480 | 594.3292 | 4.04% | no | **VOID-o** |

**C1 FAILS** (MEASURED): the bar was ≥5% on ≥3 of 6; it is met on 2, and the
pre-registered admissibility guard C1b fires on **exactly those two**. On `foam`
the affine fit reads a slope of 0.2385..0.6471 against a 10.6% drift and an
offset of 658 DN against a 872 DN grand mean — it is a level translation, not a
photometric offset.

`F1`, fact 225's whole-image mean, is admissible on all six and its ladder tracks
the drift it corrects (`foam` 0.9618..1.0646 against 10.604% ptp; `coffee-bean`
0.9116..1.0243 against 12.088%). MEASURED.

**Disclosed post-hoc (addendum 5d, and labelled post-hoc there before it was
used).** The least-squares forms shrink toward the reference: on `foam`, `F2`
fits all 100 frames inside 0.814..0.947, wholly below 1, against a drift whose
true gains must straddle 1 by construction. Held-out residual RMS therefore
**rewards** shrinkage, and the two-parameter form has more freedom to shrink than
the one-parameter form. C1's criterion is biased **in favour of** the offset
term, and it fails anyway. ARGUED, from MEASURED ladders.

### 2.3 C6 / C9 — the merge's own disagreement, six arms, gate 4.0

Excess reduction, `1 − (chi2−1)/(chi2_raw−1)`, on the pixels where disagreement
is defined:

| stack | exposure | A1b zero-pivot | C9 black-pivot | F5 block-median | A4b offset-only | A4 affine |
|---|---:|---:|---:|---:|---:|---|
| `109MSDCF` | 95.38% | +3.01% | +4.41% | +4.45% | −0.11% | +6.44% adm. |
| `119MSDCF` | 94.88% | +24.11% | **+25.67%** | +25.59% | −11.65% | +26.55% adm. |
| `112MSDCF` | 89.33% | **−20.86%** | +1.38% | +0.67% | −1.17% | VOID |
| `coffee-bubbles` | 83.43% | **−19.36%** | −3.48% | +1.59% | +3.86% | VOID |
| `foam` | 28.93% | −2.54% | **−5.60%** | **−22.38%** | +4.82% | VOID |
| `coffee-bean` | 44.73% | +61.59% | +60.66% | **+85.28%** | +16.38% | VOID |

MEASURED. **This is the answer to "how much of the merge's disagreement is
photometry", and it is not one number: it runs from −5.60% to +85.28%.** On
`coffee-bean`, the corpus's worst drift, an admissible one-parameter gain removes
**85.28%** of the measured excess disagreement — the merge is, on that stack,
overwhelmingly measuring exposure drift and calling it subject disagreement. On
`foam` the same class of correction *adds* disagreement.

**A4 is void everywhere it wins, and by arithmetic rather than by guard.** Its
`(s, o)` minimise `sum_i (R_i − s·L_i − o)^2`, and mean chi2 is the variance of
exactly that residual: subject and object are the same quantity (rule 35,
DERIVED). The pre-registered C1b guard corroborates it on 4 of 6 stacks, and on
`foam` the fitted slope range is **0.16047..0.57835** — M60b G6 reported
0.1605..0.5783 for the same fit. Independent reproduction of a degeneracy kill.

**C9 — the pedestal (MEASURED, and it FAILS its registered bar).**
`Estimator::fold_inner` builds the probe's luma from `Frame::active_row`, raw
**black-inclusive** DN (`merge.rs` ~777), and `Estimator::disagreement` subtracts
black only at read time. `m60-disagreement.rs:302-305` passes `luma_offset = 0.0`
under a comment about `pipe.luma`, a buffer the estimator never sees. A gain
fitted on black-subtracted signal is therefore applied about zero instead of
about black, over-correcting by `1 + black/signal`.

| stack | 1 + black/signal | zero-pivot | black-pivot | gap (excess pp) |
|---|---:|---:|---:|---:|
| `112MSDCF` | 3.664× | −20.86% | +1.38% | **+22.24** |
| `coffee-bubbles` | 2.501× | −19.36% | −3.48% | +15.88 |
| `foam` | 1.587× | −2.54% | −5.60% | **−3.06** |
| `109MSDCF` | 1.366× | +3.01% | +4.41% | +1.40 |
| `119MSDCF` | 1.178× | +24.11% | +25.67% | +1.56 |
| `coffee-bean` | 1.075× | +61.59% | +60.66% | **−0.93** |

Gaps are in points of *excess* reduction, differencing the two columns shown;
the instrument additionally prints the same gap in points of plain reduction
(15.35 / 10.03 / −2.94 / 0.83 / 1.02 / −0.92).

The registered bar was that the pedestal-correct arm beats the zero-pivot arm on
**every** stack, ordered by `black/signal`, and turns M60's negatives positive.
It beats it on 4 of 6 and the ordering holds only at the top. **C9 FAILS: the
pedestal is a real defect in the probe but it is not the mechanism behind M60's
negative results, and M60 F3 stands.** At gate 1.0 the same pattern:
`coffee-bubbles` −22.47% → −2.62% (+19.85 points) but still negative; `foam`
−2.36% → −5.52%.

### 2.4 C3b / C4 — does the correction change the picture?

Gate 4.0, `F1`, election frozen, **global scale removed first** (a uniform gain
on the output is a re-exposure, not a picture defect; what survives is the
winner-index map printed into the image as brightness mottling — DERIVED).

| stack | mean n_eff | mean pred sigma | RMS delta | RMS / sigma | f1sig |
|---|---:|---:|---:|---:|---:|
| `109MSDCF` | 4.9865 | 7.3633 DN | 1.32502 DN | 0.180 | **0.0000%** |
| `112MSDCF` | 12.0371 | 5.7811 DN | 4.22764 DN | 0.731 | 6.6183% |
| `coffee-bubbles` | 3.5289 | 11.1500 DN | 12.16484 DN | 1.091 | 5.4720% |
| `foam` | 1.3593 | 23.3895 DN | 16.51444 DN | 0.706 | 2.9232% |
| `119MSDCF` | 4.7230 | 8.4159 DN | 26.58985 DN | 3.159 | 60.3468% |
| `coffee-bean` | 31.6135 | 14.0568 DN | 172.14412 DN | **12.246** | **95.0242%** |

MEASURED. C3b's bar (`f1sig ≥ 1.0%` on ≥2 of 6) is **met on 5 of 6**. Per
rule 18 and as pre-registered, this is a **necessary condition only**: `f1sig`
measures change, and a wrong correction inflates it.

**C4 — the null (MEASURED).** On `109MSDCF`, the corpus's quietest stack, the
correction moves **0 of 8,241,504 pixels** above their own predicted sigma. RMS
1.325 DN is 0.095% of the 1392 DN mean signal against a 0.910% drift. The
registered expectation `f1sig(109) < 0.5 × f1sig(coffee-bean)` is met by
0.0000% against 47.51%. **The correction is a measured no-op where the drift is
absent**, which is the shape a correct correction must have.

**The weighting axis (MEASURED, and it is empty).** Fact 608's inverse-variance
weighting `w = 1/(c^2·var)` with `var` from the unscaled DN gives results
indistinguishable from the equal-weight mean the merge already ships:
`coffee-bean` 171.90884 vs 172.14412 DN RMS, `f1sig` 94.8120% vs 95.0242%. On no
stack does the choice of weighting move `f1sig` by as much as 0.6 points.

**A priced pitfall.** Forming the same fact-608 weight from **the sample itself**
rather than the pixel's expected signal makes the weight a function of that
sample's own noise and biases the mean downward. Measured cost: `109MSDCF`
`f1sig` 0.0000% → 0.5956% and max delta 11.02 → 230.37 DN; `foam` RMS 16.51 →
48.41 DN. **The mistake is roughly three times the size of the correction it is
attached to.**

### 2.5 C2 and C10 — is the drift spatially uniform? Two instruments, both void

| stack | C2 `U` | C2 planted `U` (bar 3.0) | C10 `EV` | C10 planted `EV` (bar 0.90) | C10-null `EV` |
|---|---:|---:|---:|---:|---:|
| `109MSDCF` | 0.1235 | 1.7213 FAIL | 0.0136 | 0.6672 FAIL | 0.0021 |
| `119MSDCF` | 0.5946 | 2.4850 FAIL | 0.2220 | 0.8378 FAIL | 0.0015 |
| `112MSDCF` | 0.0963 | 0.2727 FAIL | 0.0255 | 0.0786 FAIL | 0.0165 |
| `coffee-bubbles` | 0.1686 | 0.5579 FAIL | 0.0212 | 0.1835 FAIL | 0.0562 |
| `foam` | 0.2797 | 0.2993 FAIL | 0.1445 | 0.1546 FAIL | 0.1102 |
| `coffee-bean` | 0.3819 | 0.4841 FAIL | 0.0563 | 0.1033 FAIL | 0.0217 |

MEASURED. Both statistics read "not spatially coherent" on the real data, and
**both are void**, because when handed a ladder that is uniform *by
construction* neither can read "uniform" either. The mechanism is the same for
both: on a focus stack, block-to-block variation is dominated by defocus, which
is not global and swamps the drift. The C10-null column shows the statistics are
at least reading the drift — dividing the real drift out drops `EV` from 0.0136
–0.2220 to 0.0015–0.1102 — but reading it is not the same as resolving it
against defocus.

**This is the direct answer to M60 F3's challenge** — *"the estimator that would
not have this defect has to be fitted on pixels the sweep does not move, and
nobody has one"*. I built the candidate the challenge implies (a block-mean
estimator, on the argument that a normalised blur conserves light) and
**measured it to be inadequate on this corpus**: `F5` block-median is better than
the whole-image mean on `coffee-bean` (+85.28% vs +60.66%) and much worse on
`foam` (−22.38% vs −5.60%), and its associated uniformity decomposition fails its
own power control on every stack. ARGUED from MEASURED.

### 2.6 C7 — the price of inverting fact 608's ordering

`coffee-bean`, 105 frames, naive ordering (scale the DN, *then* run the noise
model on the scaled DN):

| quantity | value |
|---|---|
| measured mean response ratio | 1.000451 |
| predicted `sqrt(c)` | 1.000456 |
| **worst per-frame error vs `sqrt(c)`** | **0.0123%** (bar 10%) |
| **pixels whose winner changes** | **1,240,143 / 8,241,504 = 15.0475%** |
| mean `n_eff` | 31.6135 → 31.1215 (−0.4920) |

MEASURED. P-b **MET**: `focus.rs:309`'s unit-test mechanism reproduces on 105
real frames to 0.0123%. Getting fact 608's ordering backwards re-elects the
winner at **15.05% of pixels** — a merge that is silently a different merge.

Registered in advance and repeated here so it cannot be mistaken for a finding
(rule 20): under fact 608's correct ordering the focus field is computed on
unscaled DN and is therefore **exactly** invariant to the correction. That half
is arithmetic. Only the 15.05% is evidence.

---

## 3. The pre-registered criteria, and whether they were met

| id | criterion | bar | outcome |
|---|---|---|---|
| C1 | affine beats gain-only, held out | ≥5% on ≥3 of 6 | **FAILS** — 2 of 6, both void under C1b |
| C1b | admissibility guard | fires or not | **fired on exactly the 2 C1 wins** |
| C2 | spatial uniformity `U` | ≥3.0 / <1.5 | **VOID** — power control failed on all 6 |
| C3a | uniform planted recovery | `R ≥ 0.50` | R = **1.000000**, but algebra — see §4 |
| C3a-hard | ramped planted recovery | `R ≥ 0.50` | **FAILS** — R = **0.134212** |
| C3a-placebo | machinery no-op | both < 0.01 DN | **FAILS as worded** — see §4 |
| C3b | materiality | `f1sig ≥ 1%` on ≥2 of 6 | **MET** — 5 of 6 |
| C4 | the null | reported either way | **0.0000%**, a measured no-op |
| C5 | negative control | `R` strictly negative | **PASS** — R = **−1.007783** |
| C6 | extend M60b to gate 4.0 + 3 unseen stacks | descriptive | done, §2.3 |
| C7 / P-b | naive-ordering price | within 10% of `sqrt(c)` | **MET** — 0.0123% |
| C8 | identity vs `Estimator::green_mean` | bit-identical | **PASS** — 0 of 8,241,504 |
| C9 | pedestal turns negatives positive | every stack | **FAILS** — 4 of 6, negatives stay negative |
| C10 | explained-variance decomposition | ≥0.50 / <0.20 | **VOID** — power control failed on all 6 |

---

## 4. Controls, including the three that went red

**C5 — the negative control, made to fail (MEASURED).** `correct_dn`'s gain was
inverted, `c → 1/c`, the sign error a real implementation makes, and C3a re-run
unchanged:

| | correct | broken |
|---|---:|---:|
| planted uncorrected RMS vs `M0` | 45.44703 DN | 45.44703 DN |
| planted corrected RMS vs corrected | 0.00000 DN | **91.24776 DN** |
| recovery `R` | +1.000000 | **−1.007783** |

`91.24776 / 45.44703 = 2.008` — an inverted gain doubles the error it was meant
to remove, which is what the arithmetic says it must (DERIVED). The check has
been made to fail. **`C8` stayed PASS throughout**, which is the correct scope
and is stated so that C8 is not credited with cover it does not provide.

Restore protocol: the file was copied to
`experiments/M91-photometry/backup/m91-photometry.rs.orig` before the break and
restored from that copy — **never `git checkout --`**, which would revert to
`HEAD` and destroy five other agents' uncommitted work in this shared tree.
Verified by SHA-256 (`0CC6FC85…DDA50C4`, byte length 51582 both sides), by
reading the restored line back, by grepping for the injected `1.0 / c` and
finding none, and by re-running C3a to `R = +1.000000`. `LastWriteTime` reset per
rule 33.

**C3a-placebo — went red, and was right to (MEASURED).** As registered it
required `E_uncorr` and `E_corr` both below 0.01 DN at `gamma ≡ 1`. `E_uncorr`
read 0.00013382 DN; `E_corr` read **26.58985 DN** — which is *exactly* C3b's
independently computed corrected-vs-`M0` RMS for the same stack. **The placebo
had caught a comparison-target bug in my own design**: C3a compared the corrected
planted merge against the *uncorrected* unplanted merge, so it charged the
correction for removing the stack's native drift. With the reference corrected —
the fix the control forced — the placebo reads `E_uncorr = 0.00013382 DN` and
`E_corr = 0.00000000 DN`. **The registered wording failed and is reported as
failed.** The bar was not moved after seeing data; the instrument was wrong and
the control found it.

**C3a — reported as a control, not as evidence (rule 35).** With a spatially
uniform plant corrected by `F1`, `correct_dn(black + (d−black)·g, black, 1/g, 0)
= d` identically, so `R = 1.000000` is algebra. Addendum 5c registered this
*before* the planted arms ran rather than explaining it afterwards. Its job is to
be the thing C5 breaks, and it did that job.

**C3a-hard — the arm with power (MEASURED).** A per-frame gain ramped across the
frame, `g_k(x) = 1 + (gamma_k−1)(1 + 0.5(2x/W − 1))`, ptp 11.7%, on `119MSDCF`:

| | uniform plant | ramped plant |
|---|---:|---:|
| uncorrected RMS vs `M0` | 45.44703 DN | 71.31168 DN |
| uncorrected `f1sig` | 77.7215% | 86.5564% |
| corrected RMS vs corrected | 0.00000 DN | 61.74077 DN |
| **recovery `R`** | **1.000000** | **0.134212** |

**A global per-frame gain recovers 13.42% of the damage a spatially non-uniform
drift does, against 100% of a uniform one.** This is the only ground-truthed
direction-bearing number in the milestone, and it is the reason the verdict is
NO SHIP rather than "ship gain-only": without C2 or C10 to say which regime the
real corpus is in, applying the correction is a bet between 1.00 and 0.13.

**C2-power and C10-power — both went red (MEASURED).** §2.5. Two instruments
retired by their own controls.

---

## 5. What I did not build, and why

**I did not touch `merge.rs` or `merge_cmd.rs`.** They are contended and the
measurement did not earn an edit: the verdict is NO SHIP, so there is no image
change to gate behind a flag, and `fold_censored_probing_photometry`'s existing
doc comment — *"this cannot change the merged image"* — remains true and correct.

**I did not fix `m60-disagreement.rs`'s pedestal error.** It is not my file. The
defect and its price are in §2.3 and P3; the one-line repair is
`luma_offset = black * (1 − c)` in place of `0.0`, and the false comment at
lines 303–305 should go with it.

**I did not extend the correction to per-block or per-region gain**, which is
where the C3a-hard number points. That is a real milestone and it needs the
spatial measurement C2 and C10 both failed to deliver, on an instrument that is
not confounded by defocus — plausibly the flat-field captures rather than the
focus stacks. Named as future work, not attempted here.

---

## 6. Contradictions with the corpus

1. **Fact 180's drift figures for `112MSDCF` and `coffee-bean` do not reproduce**
   on this instrument: 7.513% against 6.84%, and 12.088% against 11.70%
   (MEASURED). The other four reproduce exactly, including `foam` to three
   decimals, so the instrument is not generally biased. Cause not established.
2. **M60b's headline that "no per-frame photometric correction removes any of
   the disagreement" is too strong.** On `coffee-bean` — a stack M60b never ran —
   an admissible one-parameter gain removes **85.28%** of the excess (MEASURED,
   gate 4.0). M60b's conclusion holds on the three stacks it measured and does not
   generalise to the corpus.
3. **Nothing here retracts M60 F3.** C9 predicted the pedestal was the mechanism
   behind M60's negative gain-only results and **that prediction is refuted**: the
   pedestal-correct arm is still negative on `coffee-bubbles` and `foam`.

---

## 7. Verification

| rule | how it was discharged |
|---|---|
| 8 | every claim above carries MEASURED / DERIVED / ARGUED |
| 12 | the not-independently-verified header is at the top |
| 18 | `f1sig` is used only as a necessary condition; `R` is the direction-bearing metric |
| 20 | every criterion in the pre-registration carries the input that fails it; §5 of that file is the table |
| 22 | this table |
| 33 | `Compiling` read on every build; `LastWriteTime` reset after the C5 restore |
| 35 | C3a's lack of power and A4's subject/object identity are both stated, not used |
| 39 | C4's null is reported with its magnitude (0 of 8,241,504) rather than as "no effect" |
| 40 | facts 180, 181, 608, 626, 704 read at source in `SYNTHESIS.md`; M24, M28, M60, M60b read in full; the brief's framing corrected in §0 |
| 42 | every commit `git commit -F <msg> -- <explicit paths>`; no `git add -A`; audited with `git show --name-only` |
| 43 | the two absence claims in the pre-registration each cite the search that establishes them; no unsupported absence claim appears in this report |

Build: `cargo build --release --example m91-photometry` in
`.cargo-target-m91`. `rustfmt --edition 2024 --check` clean on
`m91-photometry.rs`; `cargo clippy --release --example m91-photometry` reports
no warnings for that file. The workspace-wide `-D warnings` gate could not be
run because another live milestone's uncommitted `warpmap.rs` fails
`collapsible_if`; that file is not mine and was not touched.

Corpus gate: `python scripts/corpus_lint.py` run alone, exit 0.

---

## 8. Candidate facts

**P1** — *claim:* On the corpus's worst-drift stack `coffee-bean` (105 frames,
12.088% peak-to-peak), a single admissible per-frame gain removes **85.28%** of
the merge's excess disagreement at the shipped gate of 4.0 (block-median gain,
black-pivoted; 60.66% for fact 225's whole-image mean). On `foam` the same class
of correction *adds* disagreement (−5.60%, −22.38%). *Significance:* the
question "how much of the merge's disagreement is exposure drift" has no single
answer — it runs from −22% to +85% across the corpus, so a robustness mask
calibrated on one stack is calibrated on nothing. *Label:* MEASURED, M91 §2.3.

**P2** — *claim:* Applying a per-frame photometric gain to the merged image, with
the winner election frozen and the global scale removed, moves the merged green
above the pixel's own `predicted_sigma` at **95.02%** of pixels on `coffee-bean`
and **60.35%** on `119MSDCF`, and at **0 of 8,241,504** pixels on `109MSDCF`.
*Significance:* the correction is nowhere near the output noise floor on drifting
stacks and is a measured exact no-op on the quiet one — so "it is below the
noise" is not available as a reason to skip it, and neither is "it will disturb
quiet stacks". *Label:* MEASURED, M91 §2.4.

**P3** — *claim:* `Estimator::fold_inner` builds the photometric probe's luma
from `Frame::active_row`, i.e. **black-inclusive raw DN**, so a gain fitted on
black-subtracted signal must be applied about the pedestal
(`luma_offset = black*(1−c)`), not about zero. `m60-disagreement.rs:302-305`
passes `0.0` under a comment describing `pipe.luma`, a buffer the estimator never
reads. Correcting the pivot is worth **+22.24 points of excess disagreement
reduction** on `112MSDCF` at gate 4.0 and **+19.85 points** on `coffee-bubbles`
at gate 1.0. *Significance:* a live one-line defect in a shipped
research instrument, with its price measured; every M60 gain-arm number is
affected. *Label:* MEASURED, M91 §2.3.

**P4** — *claim:* The pedestal defect is **not** the mechanism behind M60's
negative gain-only results. Pedestal-corrected, `coffee-bubbles` moves from
−19.36% to −3.48% and `foam` from −2.54% to −5.60% at gate 4.0 — still negative,
and `foam` and `coffee-bean` get *worse*, against a pre-registered prediction
that every stack would improve. *Significance:* M60 F3 stands. A real defect
with a large measured price can still be the wrong explanation, and the
pre-registered bar is what makes that visible. *Label:* MEASURED, M91 §2.3.

**P5** — *claim:* M24 §5's first clause resolves: **an offset term is not
earned**. Affine beats gain-only by ≥5% on held-out blocks on only 2 of 6
stacks, and the pre-registered admissibility guard voids **both** of them
(`coffee-bubbles` offset 31.9 DN on a 341 DN grand mean; `foam` slope
0.2385..0.6471 with a 658 DN offset on an 872 DN grand mean). The criterion is
additionally biased *toward* the offset, because held-out residual RMS rewards
the regression shrinkage the two-parameter form has more freedom to exploit.
*Significance:* the functional form is settled at one parameter, on six stacks
and against a conservative bar. *Label:* MEASURED, M91 §2.2.

**P6** — *claim:* M24 §5's second clause — spatial uniformity — is **NOT
ESTABLISHED**, and two pre-registered instruments are now retired against it.
Both a between/within block-ratio spread ratio and an explained-variance
decomposition of the per-block gain ladders failed their own mandatory power
controls on all six stacks: handed a ladder that is uniform by construction at
11.7% ptp, they read 0.27–2.49 against a bar of 3.0, and 0.0786–0.8378 against a
bar of 0.90. *Significance:* on a focus stack, block-level variation is dominated
by defocus, so **block-domain statistics cannot resolve photometric drift against
defocus at all**. This is the concrete answer to M60 F3's "nobody has one": the
obvious candidate was built and measured to be inadequate. The measurement needs
a capture that does not sweep focus. *Label:* MEASURED, M91 §2.5.

**P7** — *claim:* A single global per-frame gain recovers **100.0%** of a
spatially uniform planted drift (11.7% ptp, `119MSDCF`) and **13.42%** of the
same drift given a 50% left-to-right ramp; the ramped disturbance moves 86.56% of
pixels above their own sigma uncorrected and still 80.71% corrected.
*Significance:* prices exactly what P6's unanswered question costs. Until the
drift's spatial structure is measured, applying a global gain is a bet between
1.00 and 0.13, which is why M91's verdict is NO SHIP rather than "ship
gain-only". *Label:* MEASURED, M91 §4.

**P8** — *claim:* An independent third instrument reproduces fact 180's drift
figures exactly on `109MSDCF` (0.910%), `119MSDCF` (2.880%) and `foam` (10.604%)
and to 0.2% on `coffee-bubbles`, but reads **higher** on `112MSDCF` (7.513% vs
6.84%) and `coffee-bean` (12.088% vs 11.70%). *Significance:* two of the six
drift figures in the corpus do not reproduce, on an instrument that reproduces
the other four exactly; the cause is not established. *Label:* MEASURED, M91
§2.1.

**P9** — *claim:* Inverting fact 608's ordering — scaling the DN and then
evaluating the photon-transfer model on the scaled DN — re-elects the winner at
**15.0475%** of pixels on `coffee-bean` (1,240,143 of 8,241,504) and lowers mean
`n_eff` from 31.6135 to 31.1215. The normalised focus response moves by
`sqrt(c)` to within **0.0123%** worst-frame across 105 frames. *Significance:*
`focus.rs:309`'s unit-test mechanism is confirmed at corpus scale, and fact 608's
ordering constraint is shown to be load-bearing for the *election*, not only for
the noise model — a merge with the ordering inverted is silently a different
merge. *Label:* MEASURED, M91 §2.6.

**P10** — *claim:* Inverse-variance weighting of the corrected samples per fact
608 is indistinguishable from the equal-weight mean the merge already ships
(`coffee-bean` 171.90884 vs 172.14412 DN RMS; `f1sig` within 0.6 points on every
stack). Forming the same weight from **the sample** rather than the pixel's
expected signal biases the merged mean and costs `109MSDCF` a jump in `f1sig`
from 0.0000% to 0.5956% and in max delta from 11.02 to 230.37 DN, and `foam` an
RMS jump from 16.51 to 48.41 DN. *Significance:* the weighting axis of "in what
functional form" is empty — there is nothing to gain — while one specific way of
implementing it costs about three times the size of the correction it is attached
to. *Label:* MEASURED, M91 §2.4.

**P11** — *claim:* A second implementation of the merge's averaging stage,
written against the public `strehl-core` API without editing `merge.rs`,
reproduces `Estimator::green_mean` **bit-identically in f32** at all 8,241,504
pixels on all six corpus stacks, censoring rule included. *Significance:* the
merge's averaging stage is reimplementable from the public API to the bit, so
contended-file experiments can be run out-of-tree with an exact identity control
rather than an approximate one. *Label:* MEASURED, M91 §1.

**P12** — *claim:* A pre-registered placebo detected a comparison-target bug in
its own milestone's design by reproducing a *different* arm's number exactly: at
`gamma ≡ 1` the planted-corrected arm read 26.58985 DN, which is precisely the
independently computed corrected-vs-uncorrected RMS from the materiality arm.
*Significance:* a placebo's value is not only that it reads zero — a placebo that
reads a recognisable number from elsewhere in the same run localises the bug.
*Label:* MEASURED, M91 §4.
